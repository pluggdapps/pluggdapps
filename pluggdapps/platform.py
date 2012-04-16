# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-


import pkg_resources         as pkg
import logging

from   pluggdapps.plugin     import Plugin, query_plugin, query_plugins, \
                                    pluginname, plugin_init
import pluggdapps.config     as config
import pluggdapps.log        as logm
from   pluggdapps.interfaces import IApplication
import pluggdapps.util       as h

log = logging.getLogger(__name__)

DEFAULT_SERVER = 'httpioserver'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 5000

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "pluggdapps global configuration settings."

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
    'default' : None,
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
    def boot( cls, inifile=None, level=None ):
        """Do the following,
        * Boot platform using an optional master configuration file `inifile`.
        * Load pluggdapps packages.
        * Init plugins

        ``gs``,
            Global settings
        """
        from  pluggdapps import appsettings, ROOTAPP
        appsett = config.loadsettings( inifile )
        appsettings['root'].update( appsett.pop('root', {}) )
        appsettings.update( appsett )
        cls.appsettings = appsettings

        # Setup logger 
        logsett = h.settingsfor( 'logging.', appsettings['root']['platform'] )
        logsett['level'] = level or logsett['level']
        logm.setup( logsett )
        log.info( 'Loaded application settings for %r', appsettings.keys() )

        # Parse master ini file for application mount rules and generate a map
        cls.map_subdomains, cls.map_scripts = cls._mountmap()
        # Load packages specific to pluggdapps
        cls._loadpackages( appsettings )
        # Initialize plugin data structures
        plugin_init()
        # Boot applications
        apps = query_plugins( ROOTAPP, IApplication )
        log.info( "%d applications found, booting them ..." % len(apps) )
        for a in apps :
            appname = pluginname(a)
            log.debug( 'Booting application %r ...', appname )
            a.boot( appsettings.get( appname, {} )) 

        return appsettings

    def serve( self ):
        from pluggdapps import ROOTAPP
        from pluggdapps.interfaces import IServer

        rootsett = self.appsettings['root']
        servername = rootsett.get('servername', DEFAULT_SERVER)
        self.server = query_plugin( ROOTAPP, IServer, servername, self )
        server.start()  # Blocks !

    def appfor( self, request ):
        if ':' in request.host :
            host, port = request.host.split(':', 1)
            port = int(port)
        else :
            port = 80 if request.protocol == 'http' else 443

        try    : subdomain, site, tld = host.rsplit('.', 3)
        except : subdomain = None

        for subdom, appname in self.map_subdomains.items() :
            if subdom == subdomain : break
        else :
            for script, appname in self.map_scripts.items() :
                if request.path.startswith( script ) : break
            else :
                appname = self.map_scripts['/']
        return appname

    @classmethod
    def _loadpackages( self, appsettings ):
        """Import all packages from this python environment.

        TODO : Only import packages specific to pluggdapps"""
        packages = []
        pkgs = pkg.WorkingSet().by_key # A dictionary of pkg-name and object
        for pkgname, d in sorted( pkgs.items(), key=lambda x : x[0] ) :
            info = h.call_entrypoint(d,  'pluggdapps', 'package', appsettings)
            if info == None : continue
            __import__( pkgname )
            packages.append( pkgname )
        log.info( "%s pluggdapps packages loaded" % len(packages) )
        return packages

    @classmethod
    def _mountmap( self ):
        subdomains, scripts = {}, {}
        for key, sett in self.appsettings.items() :
            if key.startswith('app:') :
                appname = key.split(':')[1].strip()
                subdomain = sett.get('mount_subdomain', None)
                if subdomain :
                    subdomain.setdefault( subdomain, [] ).append( appname )
                script = sett.get('mount_script', None)
                if script :
                    script.setdefault( script, [] ).append( appname )
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

