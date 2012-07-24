# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

"""Handles platform related functions, like parsing configuration settings,
booting applications, loading plugins. And all of this are handled by the
singleton class:`Pluggdapps`. It also inherits from class:`Port` class
providing erlang-port interface to netscale systems.

While booting, it instanstiates the following global dictionaries, all of them
are read only after they are created in boot() call.

settings 
    refer to :mod:`pluggdapps.config` for more information

m_subdomains
    a mapping of subdomain (optionally dot seperated) name to application
    instance.

m_scripts
    a mapping of script (prefixed with root slash) name to application
    instance.
"""

from   configparser          import SafeConfigParser

import pluggdapps
from   pluggdapps.erlport    import Port
from   pluggdapps.const      import ROOTAPP, MOUNT_SUBDOMAIN, MOUNT_SCRIPT
from   pluggdapps.config     import loadsettings, sec2app
from   pluggdapps.plugin     import Singleton, ISettings, applications, \
                                    query_plugin, query_plugins, IWebApp
from   pluggdapps.interfaces import IRequest, IResponse
import pluggdapps.utils as h

_default_settings = ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for pluggdapps section, which has system wide "\
    "scope."

settings      = {}    # Complete configuration settings
m_subdomains  = {}    # Mapping url to application based on subdomain
m_scripts     = {}    # Mapping url to application based on script

class Pluggdapps( Singleton, Port ):

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )

    def bootapps( self ):
        """Boot all loaded application. Web-Apps are loaded when the
        system is booted via boot() call. Apps are booted only when an
        explicit call is made to this method."""
        appnames = []
        for appname in sorted( self.apps ) :
            self.loginfo( "Booting application %r ..." % appname, [] )
            self.apps[appname].onboot()
            appnames.append( appname )
        return appnames

    def makerequest( self, conn, address, startline, headers, body ):
        # Parse request start-line
        method, uri, version = h.parse_startline( startline )
        uriparts = h.parse_url( uri, headers.get('Host', None) )

        # Resolve application
        (typ, key, appname) = self.appresolve( uriparts, headers, body )
        app = query_plugin( appname, IWebApp, appname )

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
            app = query_plugin( appname, IWebApp, appname )
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

    def shutdown( self ):
        for appname in sorted( self.apps ) :
            self.loginfo( "Shutting down application %r ..." % appname, [] )
            self.apps[appname].shutdown()

    apps = {}

    @classmethod
    def boot( cls, inifile, *args, **kwargs ):
        """Boot sequence
        * Boot platform using master configuration file, refer module
          `pluggdapps.config`.
        * Cache application mount points to speed-up request resolution on apps.
        * Load pluggdapps packages.
        * Initalize plugins
        * Boot applications.
        """
        global settings, m_subdomains, m_scripts
        cls.inifile = inifile
        settings = loadsettings( inifile )

        # Instiantiate `this` singleton !!
        pa = query_plugin( ROOTAPP, ISettings, 'pluggdapps', *args, **kwargs )

        # Mount webapp instances for subdomains and scripts. ROOTAPP will not be
        # mounted.
        for instkey, appsett in list( settings.items() ) :
            if instkey in [ 'DEFAULT', app2sec(ROOTAPP) ] : continue
            key, t, v, config = instkey
            appname = sec2app( key )
            app = query_plugin( appname, IWebApp, appname, appsett )
            cls.apps[ appname ] = app
            app.pa, app.subdomain, app.script = pa, None, None
            if t == MOUNT_SUBDOMAIN :
                m_subdomains.setdefault( v, app )
                app.subdomain = v
            elif t == MOUNT_SCRIPT :
                m_scripts.setdefault( v, app )
                app.script = v
        return pa


    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings


def platform_logs( pa, levelstr='info' ) :
    fn = getattr( log, levelstr )
    fn( "%s interfaces defined and %s plugins loaded",
        len(PluginMeta._interfmap), len(PluginMeta._pluginmap) )
    fn( "%s applications loaded", len(applications()) ) 
    fn( "%s pluggdapps packages loaded", len(pluggdapps.packages) )


def mount_logs( pa ):
    for appname in sorted( pa.apps ) :
        mount = m_subdomains.get( appname, None )
        if mount :
            log.debug( "%r mounted on subdomain %r", appname, mount )
        else :
            mount = m_scripts.get( appname, None )
            log.debug( "%r mounted on scripts %r", appname, mount )

