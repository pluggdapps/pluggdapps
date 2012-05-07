# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

"""Handles platform related functions, like parsing configuration settings,
booting applications, setting up logging, loading plugins and application
mount points. All of these functions are carried out by :class:`Platform`
plugin, which is a singleton class."""

import logging
from   urllib.parse          import urlsplit
from   configparser          import SafeConfigParser

from   pluggdapps import packages
from   pluggdapps.const import ROOTAPP
from   pluggdapps.config import ConfigDict, settingsfor
from   pluggdapps.plugin import Singleton, ISettings, log_statistics, \
                                query_plugin, query_plugins
from   pluggdapps.interfaces import IApplication
import pluggdapps.utils      as h

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

class Platform( Singleton ):

    @classmethod
    def boot( cls, inifile ):
        """Do the following,
        * Boot platform using an optional master configuration file `inifile`.
        * Setup logging.
        * Cache application mount points to speed-up request resolution on
          apps.
        * Load pluggdapps packages.
        * Initalize plugins
        * Boot applications.
        """
        cls.appsettings = appsettings = loadsettings( inifile )

        # Mount configurations for application (on subdomains and scriptpaths)
        cls.m_subdomains, cls.m_scripts = {}, {}
        for appname, sett in list( appsettings.items() ) :
            subdomain = sett.get('DEFAULT', {}).get('mount_subdomain', None)
            if subdomain :
                cls.m_subdomains.setdefault( subdomain, appname )
            script = sett.get('DEFAULT', {}).get('mount_script', None)
            if script :
                cls.m_scripts.setdefault( script, appname )
        cls.m_scripts.setdefault( '/', 'rootapp' )

        # Load applications
        # Note : All applications are expected to be singleton objects. And
        #   they are first instantiated here.
        # Note1 : Create a singleton platform object. Make sure that no query_*
        #   is called before instantiating application singletons.
        platform.apps = query_plugins( '', IApplication, appsettings )
        platform = query_plugin( ROOTAPP, ISettings, 'platform' )
        platform.rootapp = query_plugin( ROOTAPP, IApplication, ROOTAPP )

        # Setup loggings
        logsett = settingsfor( 'logging.', platform.rootapp )
        setuplog( rootapp, inifile, loglevel=loglevel )

        # Print information about what has gone this far ...
        log.info( "%s pluggdapps packages loaded", len(packages) )
        log_statistics()

        # Mount and Boot applications
        for app in apps :
            appname = app.appname
            mount = cls.m_subdomains.get( appname, None )
            if mount :
                log.debug( "%r mounted on subdomain %r", appname, mount )
            else :
                mount = cls.m_scripts.get( appname, None )
                if mount :
                    log.debug( "%r mounted on scripts %r", appname, mount )
                else :
                    cls.m_scripts.setdefault( appname, appname )
                    log.debug( "%r mounted on scripts %r", appname, appname )
            log.debug( "Booting application %r ...", appname )
            app.onboot( app.settings )
            app.platform = platform
        return platform

    def shutdown( self ):
        log.info( "Shutting down platform ..." )
        for app in query_plugins( '', IApplication ) :
            log.debug( "Shutting down application %r ...", app.appname )
            app.shutdown( app.settings )

    def serve( self ):
        """Use :class:`IServer` interface and `servername` settings to start a
        http server."""
        from pluggdapps.interfaces import IServer

        servername = self['servername']
        self.server = query_plugin( ROOTAPP, IServer, servername, self )
        self.server.start()  # Blocks !

    def appfor( self, startline, headers, body ):
        """Resolve applications for `request`."""
        method, uri, version = h.parse_startline( startline )
        host = headers.get("Host") or "127.0.0.1"
        _, _, path, _, _ = urlsplit( uri )

        if ':' in host :
            host, port = host.split(':', 1)

        try    : subdomain, site, tld = host.rsplit('.', 3)
        except : subdomain = None

        if subdomain :
            for subdom, appname in list( cls.m_subdomains.items() ) :
                if subdom == subdomain : break
            script = ''
        else :
            for script, appname in list( cls.m_scripts.items() ) :
                if script != '/' and path.startswith( script ) : break
            else :
                appname = cls.m_scripts['/']
                script = ''
        return appname


    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        return settings
