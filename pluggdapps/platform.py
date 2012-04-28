# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-


import pkg_resources         as pkg
import logging, urlparse

from   pluggdapps.config     import ConfigDict, settingsfor
from   pluggdapps.plugin     import Plugin, query_plugin, query_plugins, \
                                    pluginname, plugin_init
from   pluggdapps.config     import loadsettings, getsettings, app2sec
from   pluggdapps.interfaces import IApplication
import pluggdapps.helper     as h

log = logging.getLogger(__name__)

_default_settings = ConfigDict()
_default_settings.__doc__ = (
    "Platform configuration settings are equivalent to global configuration "
    "settings. Nevertheless these configurations are to be modified only "
    "under [plugin:platform] section, not the [DEFAULT] section. And "
    "[plugin:platform] section is to be configured in the master ini file.")

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
    'help'    : "If logs have to be send to terminal should you want it "
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
        from  pluggdapps import apps, ROOTAPP
        log.info( 'Booting platform from %r ...', inifile )
        cls.inifile = inifile
        # Setup logger 
        cls.setuplog( inifile )
        # Load packages specific to pluggdapps
        cls._loadpackages()
        # Load application settings
        cls.appsettings = appsettings = loadsettings( inifile )
        # Parse master ini file for application mount rules and generate a map
        cls.map_subdomains, cls.map_scripts = cls._mountmap( appsettings )
        # Initialize plugin data structures
        plugin_init()
        # Load applictions
        for app in query_plugins( ROOTAPP, IApplication ) :
            appname = pluginname( app )
            app.settings = cls.appsettings[ appname ]
            log.debug( "Booting application %r ...", appname )
            app.boot( app.settings ) 
            apps[ appname ] = app

    def serve( self ):
        """Use :class:`IServer` interface and `servername` settings to start a
        http server."""
        from pluggdapps import ROOTAPP
        from pluggdapps.interfaces import IServer

        servername = self['servername']
        self.server = query_plugin( ROOTAPP, IServer, servername, self )
        self.server.start()  # Blocks !

    def shutdown( self ):
        from pluggdapps import get_apps
        log.info( "Shutting down platform ..." )
        for appname, app in get_apps().items() :
            log.debug( "Shutting down application %r ...", appname )
            app.shutdown( app.settings )

    def appfor( self, startline, headers, body ):
        """Resolve applications for `request`."""
        from  pluggdapps import get_apps
        method, uri, version = h.parse_startline( startline )
        host = headers.get("Host") or "127.0.0.1"
        _, _, path, _, _ = urlparse.urlsplit( h.native_str(uri) )

        if ':' in host :
            host, port = host.split(':', 1)

        try    : subdomain, site, tld = host.rsplit('.', 3)
        except : subdomain = None

        if subdomain :
            for subdom, appnames in cls.map_subdomains.items() :
                if subdom == subdomain : break
            script = ''
        else :
            for script, appnames in cls.map_scripts.items() :
                if script != '/' and path.startswith( script ) : break
            else :
                appnames = [ cls.map_scripts['/'] ]
                script = ''
        return get_apps()[appname]

    on_subdomains = property( lambda s : s.map_subdomains )
    on_scripts = property( lambda s : s.map_scripts )  

    @classmethod
    def setuplog( cls, inifile=None, procid=None ):
        """Setup logging."""
        from   pluggdapps        import ROOTAPP
        import pluggdapps.log    as logm
        from   pluggdapps.compat import configparser

        if inifile :
            cp = configparser.SafeConfigParser()
            cp.read( inifile )
            level = cp.defaults().get('logging.level', None)
        else :
            level = None

        logsett = dict([ (k[8:], v) for k,v in _default_settings.items()
                                    if k.startswith('logging.') ])

        logsett['level'] = level or logsett['level']
        logsett['filename'] = logm.logfileusing( procid, logsett['filename'] )
        logm.setup( logsett )

    @classmethod
    def _loadpackages( self ):
        """Import all packages from this python environment."""
        packages = []
        pkgs = pkg.WorkingSet().by_key # A dictionary of pkg-name and object
        for pkgname, d in sorted( pkgs.items(), key=lambda x : x[0] ) :
            info = h.call_entrypoint(d,  'pluggdapps', 'package' )
            if info == None : continue
            __import__( pkgname )
            packages.append( pkgname )
        log.debug( "%s pluggdapps packages loaded" % len(packages) )
        return packages

    @classmethod
    def _mountmap( cls, appsettings ):
        subdomains, scripts = {}, {}
        for appname, sett in appsettings.items() :
            subdomain = sett.get('DEFAULT', {}).get('mount_subdomain', None)
            if subdomain :
                subdomain.setdefault( subdomain, [] ).append( appname )
            script = sett.get('DEFAULT', {}).get('mount_script', None)
            if script :
                scripts.setdefault( script, [] ).append( appname )
        scripts.setdefault( '/', [] ).append( 'rootapp' )
        log.debug( "%s applications mounted on subdomains", len(subdomains) )
        log.debug( "%s applications mounted on script-path", len(scripts) )
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
        # Logging level
        level = settings['logging.level']
        level = getattr(logging, level.upper()) if level != 'none' else None
        settings['logging.level'] = level
        return settings
