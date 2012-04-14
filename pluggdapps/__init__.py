# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import pkg_resources         as pkg
from   ConfigParser          import SafeConfigParser

from   pluggdapps.plugincore import plugin_init, query_plugin, query_plugins,\
                                    pluginname, pluginclass
import pluggdapps.config     as config

# Load all interface specifications and plugins defined by this package.
import pluggdapps.interfaces
import pluggdapps.plugincore
import pluggdapps.commands
import pluggdapps.evserver
import pluggdapps.request
import pluggdapps.response
import pluggdapps.application

__version__ = '0.1dev'
ROOTAPP = 'root'
DEFAULT_SERVER = 'httpioserver'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 5000

appsettings = { 'root' : {} }
"""Dictionary of plugin configurations. Note that,

  * Every mountable application is a plugin object implementing
    :class:`IApplication` interface specification.

  * Platform configuration file (master ini file) can specify separate 
    configuration files for each loaded application like,
     [app:<appname>]
        use = config:<ini-file>

  * `appsettings` dictionary will have the following structure,
      { <appname> : { 'DEFAULT'    : { <option> : <value>, ... },
                      <pluginname> : { <option> : <value>, ... },
                      ...
                    },
        ...
      }
    where, <appname> is plugin-name implementing :class:`IApplication`
    interface.

  * `appsettings` structure will be populated based on default settings, by
    parsing configuration files (ini files) and web-admin's storage backend.

  * settings in configuration file will override default settings and
    web-admin's settings will override settings from configuration file.

  * structure stored in web-admin's backend will be similar to the
    `appsettings` structure described above.

  * `appsettings` will be populated during platform boot-up time.
"""

class Platform( object ):

    def boot( inifile=None ):
        """Do the following,
        * Boot platform using an optional master configuration file `inifile`.
        * Load pluggdapps packages.
        * Init plugins
        """
        global appsettings
        appsett = config.loadsettings( inifile ) if inifile else {}
        appsettings['root'].update( appsett.pop('root', {}) )
        appsettings.update( appsett )

        # Parse master ini file for application mount rules and generate a map
        self.map_subdomains, self.map_scripts = self._mountmap()
        # Load packages specific to pluggdapps
        self._loadpackages()
        # Initialize plugin data structures
        plugin_init()
        # Boot applications
        [ a.boot( appsettings.get( pluginname(app), {} )) 
          for a in query_plugins(ROOTAPP, IApplication) ]

        self.appsettings = appsettings
        return appsettings

    def serve( self ):
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

    def _loadpackages( self ):
        """Import all packages from this python environment.

        TODO : Only import packages specific to pluggdapps"""
        pkgnames = pkg.WorkingSet().by_key.keys()
        [ __import__(pkgname) for pkgname in sorted( pkgnames ) ]
        logging.info( "%s pluggdapps packages loaded" % len( _package.keys() ))

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
