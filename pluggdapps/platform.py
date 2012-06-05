# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

"""Handles platform related functions, like parsing configuration settings,
booting applications, setting up logging, loading plugins and application
mount points. All of these functions are carried out by :class:`Platform`
plugin, which is a singleton class."""

import logging
from   configparser          import SafeConfigParser

from   pluggdapps import packages
from   pluggdapps.const import ROOTAPP
from   pluggdapps.config import ConfigDict, settingsfor, loadsettings
from   pluggdapps.plugin import Singleton, ISettings, applications, \
                                query_plugin, query_plugins, IApplication
from   pluggdapps.interfaces import IRequest, IResponse
import pluggdapps.utils as h
import pluggdapps.log as logm

log = logging.getLogger(__name__)

_default_settings = ConfigDict()
_default_settings.__doc__ = (
    "Platform configuration settings are equivalent to global configuration "
    "settings. Nevertheless these configurations are to be modified only "
    "under [plugin:platform] section, not the [DEFAULT] section. And "
    "[plugin:platform] section is to be configured in the master ini file.")

_default_settings['debug'] = {
    'default' : False,
    'types'   : (bool,),
    'help'    : "If True, execute platform in debug mode."
}
_default_settings['servername'] = {
    'default' : 'httpioserver',
    'types'   : (str,),
    'help'    : "IServer plugin to be used as http server."
}
_default_settings['retry_after'] = {
    'default' : 2,
    'types'   : (int,),
    'help'    : "Time in seconds to retry after a 503 (Service Unavailable "
                "response. This will go into 'Retry-After' response header."
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
_default_settings['logging.format'] = {
    'default' : ("[%(levelname)1.1s proc:%(process)d %(asctime)s "
                 "%(module)s:%(lineno)d]"),
    'types'   : (str,),
    'help'    : "Format string for log entries."
}


class Platform( Singleton ):

    @classmethod
    def boot( cls, inifile, loglevel=None ):
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

        # Before instantiating any plugin, instantiate rootapp
        rootapp = query_plugin( ROOTAPP, IApplication, ROOTAPP, appsettings )

        # Instantiate the platform singleton
        platform = query_plugin( rootapp, ISettings, 'platform' )

        # Load applications
        # Note : All applications are expected to be singleton objects. And
        #   they are first instantiated here.
        platform.apps = query_plugins( '', IApplication, appsettings )
        platform.rootapp = query_plugin( ROOTAPP, IApplication, ROOTAPP )

        # query_* calls can be made only after platform singletons and 
        # application singletons.

        # Setup loggings
        logsett = settingsfor( 'logging.', platform )
        logsett['level'] = loglevel or logsett['level']
        logm.setup( logsett )

        # Mount applications
        subdomains_m = { v : k for k, v in cls.m_subdomains.items() }
        scripts_m = { v : k for k, v in cls.m_scripts.items() }
        for app in platform.apps :
            appname = app.appname
            app.platform = platform
            app.subdomain = subdomains_m.get( appname, None )
            if app.subdomain == None :
                app.script = scripts_m.get( appname, None )
                if app.script == None :
                    cls.m_scripts.setdefault( appname, appname )
                    app.script = appname
            else :
                app.script = None
        return platform

    def bootapps( self ):
        # Boot applications
        for app in self.apps :
            log.debug( "Booting application %r ...", app.appname )
            app.onboot( app.settings )

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
        self.server = query_plugin( ROOTAPP, IServer, servername )
        self.server.start()  # Blocks !

    def make_request( self, conn, address, startline, headers, body ):
        # Parse request start-line
        method, uri, version = h.parse_startline( startline )
        uriparts = h.parse_url( uri, headers.get('Host', None) )

        # Resolve application
        (typ, key, appname) = self.appresolve( uriparts, headers, body )
        app = query_plugin( appname, IApplication, appname )

        # IRequest plugin
        request = query_plugin(
                        app, IRequest, app['IRequest'], conn, address, 
                        method, uri, uriparts, version, headers, body )
        response = query_plugin( app, IResponse, app['IResponse'], self )
        request.response = response

        return request

    def appresolve( self, uriparts, headers, body ):
        """Resolve application for `request`."""
        doms = uriparts['hostname'].split('.')
        doms = doms[1:] if doms[0] == 'www' else doms
        # A subdomain available ?
        subdomain = doms[0] if len(doms) > 2 else None

        mountedat = ()
        if subdomain :
            for subdom, appname in self.m_subdomains.items() :
                if subdom == subdomain :
                    mountedat = ('subdomain', subdom, appname)
                    break
        if not mountedat :
            for script, appname in self.m_scripts.items() :
                if script == '/' : continue
                if uriparts['path'].startswith( script ) :
                    uriparts['script'] = script
                    uriparts['path'] = uriparts['path'][len(script):]
                    mountedat = ('script', script, appname)
                    break
            else :
                mountedat = ( 'script', '/', self.m_scripts['/'] )
        return mountedat

    def baseurl( self, request, appname=None, scheme=None, auth=False,
                 hostname=None, port=None ):
        """Construct the base URL for request. If `appname` is supplied and
        different from request's app, then base-url will be computed for the
        application `appname`.
        Key word arguments can be used to override the computed valued."""
        app, uriparts = request.app, request.uriparts
        if appname != app.appname :     # base_url for a different app
            app = query_plugin( appname, IApplication, appname )
            if request.app.subdomain :  # strip off this app's subdomain
                apphost = uriparts['hostname'][len(request.app.subdomain)+1:]
            else :                      # else, use the hostname as it is
                apphost = uriparts['hostname']
            if app.subdomain :
                apphost = app.subdomain + '.' + apphost
            app_script = app.appscript  # It might or might not be empty
        else :
            apphost, app_script = uriparts['hostname'], uriparts['script']

        # scheme
        scheme = scheme or uriparts['scheme']
        url = scheme + '://'
        # username, password
        if auth and urlparts.username and urlparts.password :
            url += urlparts.username + ':' + urlparts.password + '@'
        # hostname, port
        url += hostname or apphost
        if port :
            url += ':' + str(port)
        elif uriparts['port'] :
            app_port = h.port_and_scheme( scheme, uriparts['port'] )
            url += (':' + app_port) if app_port else ''
        # script
        uri += app_script

        return url


    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        sett = super().normalize_settings( settings )
        sett['debug'] = h.asbool( sett['debug'] )
        sett['logging.stderr'] = h.asbool( sett['logging.stderr'] )
        sett['logging.file_maxsize'] = h.asint( sett['logging.file_maxsize'] )
        sett['logging.file_maxbackups'] = \
                                    h.asint( sett['logging.file_maxbackups'] )
        sett['logging.color'] = h.asbool( sett['logging.color'] )
        # Logging level
        level = sett['logging.level']
        level = getattr(logging, level.upper()) if level != 'none' else None
        sett['logging.level'] = level
        return sett

def platform_logs( platform, levelstr='info' ) :
    fn = getattr( log, levelstr )
    fn( "%s interfaces defined and %s plugins loaded",
        len(PluginMeta._interfmap), len(PluginMeta._pluginmap) )
    fn( "%s applications loaded", len(applications()) ) 
    fn( "%s pluggdapps packages loaded", len(packages) )


def mount_logs( platform ):
    for app in platform.apps :
        appname = app.appname
        mount = platform.m_subdomains.get( appname, None )
        if mount :
            log.debug( "%r mounted on subdomain %r", appname, mount )
        else :
            mount = platform.m_scripts.get( appname, None )
            log.debug( "%r mounted on scripts %r", appname, mount )


# Unit-test
from pluggdapps.unittest import UnitTestBase
from pluggdapps.interfaces import IUnitTest
from pluggdapps.plugin import plugins
from pluggdapps.core import PluginMeta, pluginname
from random import choice

class UnitTest_Plugin( UnitTestBase, Singleton ):

    def setup( self ):
        super().setup()

    def test( self ):
        self.test_pluginmeta()
        super().test()

    def teardown( self ):
        super().teardown()

    #---- Test cases

    def test_pluginmeta( self ):
        self.log.info("Testing plugin-meta() ...")
        # Test plugins
        assert sorted( PluginMeta._pluginmap.keys() ) == sorted( plugins() )
        nm = choice( list( PluginMeta._pluginmap.keys() ))
        info = PluginMeta._pluginmap[nm]
        assert info['name'] == pluginname( info['cls'] )

        # Test Singleton, master_init
        p = query_plugin( ROOTAPP, IUnitTest, 'unittest_plugin' )
        assert p == self
        assert p.__init__.__func__.__name__ == 'masterinit'
        assert p.__init__._original.marker == 'UnitTestBase'


class UnitTest_Plugin1( UnitTestBase ):

    def __init__( self, *args, **kwargs ):
        pass
    __init__.marker = 'UnitTest_Plugin1'

    def setup( self ):
        super().setup()

    def test( self ):
        self.test_pluginmeta()
        super().test()

    def teardown( self ):
        super().teardown()

    #---- Test cases

    def test_pluginmeta( self ):
        self.log.info("Testing singleton and master_init ...")
        p = query_plugin( ROOTAPP, IUnitTest, 'unittest_plugin1' )
        assert p != self
        assert p.__init__.__func__.__name__ == 'masterinit'
        assert p.__init__._original.marker == 'UnitTest_Plugin1'

