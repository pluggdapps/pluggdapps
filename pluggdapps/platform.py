# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-


import pkg_resources         as pkg
import logging, os

from   pluggdapps.plugin     import Plugin, query_plugin, query_plugins, \
                                    pluginname, plugin_init
from   pluggdapps.config     import loadsettings, getsettings
import pluggdapps.log        as logm
from   pluggdapps.interfaces import IApplication
import pluggdapps.util       as h

log = logging.getLogger(__name__)

DEFAULT_SERVER = 'httpioserver'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 5000

_default_settings = h.ConfigDict()
_default_settings.__doc__ = (
    "Platform configuration settings are equivalent to global configuration "
    "settings." )

_default_settings['servername']  = {
    'default' : 'httpioserver',
    'types'   : (str,),
    'help'    : "IServer plugin to as http server."
}
_default_settings['logging.level']  = {
    'default' : 'debug',
    'types'   : (str,),
    'options' : [ 'debug', 'info', 'warning', 'error', 'none' ],
    'help'    : "Set Python log level. If 'none', logging configuration won't "
                "be touched.",
}
_default_settings['logging.stderr'] = {
    'default' : True,
    'types'   : (bool,),
    'help'    : "Send log output to stderr (colorized if possible).",
}
_default_settings['logging.filename'] = {
    'default' : 'apps.log',
    'types'   : (str,),
    'help'    : "Path prefix for log files. Note that if you are "
                "running multiple processes, log_file_prefix must be "
                "different for each of them (e.g. include the port number).",
}
_default_settings['logging.file_maxsize'] = {
    'default' : 100*1024*1024,
    'types'   : (int,),
    'help'    : "max size of log files before rollover.",
}
_default_settings['logging.file_maxbackups'] = {
    'default' : 10,
    'types'   : (int,),
    'help'    : "number of log files to keep.",
}
_default_settings['logging.color'] = {
    'default' : True,
    'types'   : (bool,),
    'help'    : "If logs have to be send to terminal, should you want it "
                "colored."
}


class Platform( Plugin ):

    @classmethod
    def boot( cls, inifile=None, loglevel=None ):
        """Do the following,
        * Boot platform using an optional master configuration file `inifile`.
        * Setup logging.
        * Cache application mount points to speed-up request resolution on
          apps.
        * Load pluggdapps packages.
        * Initalize plugins
        * Boot applications.

        ``inifile``,
            Master configuration file.
        ``loglevel``,
            loglevel to use. This will override default 'logging.level'.
        """
        from  pluggdapps import appsettings, ROOTAPP
        log.info( 'Booting platform ...' )
        appsettings.update( loadsettings( inifile ))
        cls.appsettings = appsettings

        # Setup logger 
        cls.setuplog( level=loglevel )

        # Parse master ini file for application mount rules and generate a map
        cls.map_subdomains, cls.map_scripts = cls._mountmap()
        # Load packages specific to pluggdapps
        cls._loadpackages( appsettings )
        # Initialize plugin data structures
        plugin_init()
        # Boot applications
        apps = query_plugins( ROOTAPP, IApplication )
        for app in apps :
            appname = pluginname(app)
            log.debug( "Booting application %r ...", appname )
            app.boot( appsettings[appname] ) 

        return appsettings

    def serve( self ):
        """Use :class:`IServer` interface and `servername` settings to start a
        http server."""
        from pluggdapps import ROOTAPP
        from pluggdapps.interfaces import IServer

        servername = getsettings(ROOTAPP, plugin='platform', key='servername')
        self.server = query_plugin( ROOTAPP, IServer, servername, self )
        self.server.start()  # Blocks !

    def shutdown( self ):
        from pluggdapps import ROOTAPP
        log.info( "Shutting down platform ..." )
        for app in query_plugin( ROOTAPP, IApplication ) :
            appname = pluginname(app)
            log.debug( "Shutting down application %r ...", appname )
            app.shutdown( appsettings[appname] )

    def appfor( self, request ):
        """Resolve applications for `request`."""
        if ':' in request.host :
            host, port = request.host.split(':', 1)
            port = int(port)
        else :
            port = 80 if request.protocol == 'http' else 443

        try    : subdomain, site, tld = host.rsplit('.', 3)
        except : subdomain = None

        for subdom, appname in cls.map_subdomains.items() :
            if subdom == subdomain : break
        else :
            for script, appname in cls.map_scripts.items() :
                if request.path.startswith( script ) : break
            else :
                appname = cls.map_scripts['/']
        return appname

    @classmethod
    def setuplog( cls, level=None, procid=None ):
        """Setup logging."""
        from pluggdapps import ROOTAPP
        logsett = h.settingsfor( 'logging.', getsettings(ROOTAPP, plugin='platform' ))
        logsett['level'] = level or logsett['level']
        logsett['filename'] = logm.logfileusing( procid, logsett['filename'] )
        logm.setup( logsett )

    @classmethod
    def _loadpackages( self, appsettings ):
        """Import all packages from this python environment."""
        packages = []
        pkgs = pkg.WorkingSet().by_key # A dictionary of pkg-name and object
        for pkgname, d in sorted( pkgs.items(), key=lambda x : x[0] ) :
            info = h.call_entrypoint(d,  'pluggdapps', 'package', appsettings)
            if info == None : continue
            __import__( pkgname )
            packages.append( pkgname )
        log.debug( "%s pluggdapps packages loaded" % len(packages) )
        return packages

    @classmethod
    def _mountmap( cls ):
        subdomains, scripts = {}, {}
        for appname, sett in cls.appsettings.items() :
            subdomain = sett.get('DEFAULT', {}).get('mount_subdomain', None)
            if subdomain :
                subdomain.setdefault( subdomain, [] ).append( appname )
            script = sett.get('DEFAULT', {}).get('mount_script', None)
            if script :
                script.setdefault( script, [] ).append( appname )
        log.debug( "%s applications mountable on subdomains", len(subdomains) )
        log.debug( "%s applications mountable on script-path", len(scripts) )
        return subdomains, scripts

    # ISettings interface methods
    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        settings['logging.stderr'] = h.asbool( settings['logging.stderr'] )
        settings['logging.file_maxsize'] = \
                h.asint( settings['logging.file_maxsize'] )
        settings['logging.file_maxbackups'] = \
                h.asint( settings['logging.file_maxbackups'] )
        settings['logging.color'] = h.asbool( settings['logging.color'] )
        return settings
