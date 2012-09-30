# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

"""Handles platform related functions, like parsing configuration settings,
loading plugins (and applications). As noted elsewhere, a plugin is just a
dictionary of configuration settings for a class object implementing a one or
more interface specifications. Configuration settings is central to
plugin system.

Master configuration file:
--------------------------

Platform's boot sequence expect a ini-file regarded as master configuration
file. Settings in this master configuration file will override package default
settings for plugins and other sections. Any configuration section not
prefixed with 'plugin:' is considered as special section, which are explained
further below.

An example master configuration file,

  base.ini
  --------

  [DEFAULT]
  <option> = <value>
  ...

  [pluggdapps]
  <option> = <value>
  ...

  [plugin:<pluginname>]
  <option> = <value>
  ...

  [plugin:<pluginname>]
  ...

Shall be parsed to settings like,

  settings = {
      pluggdapps            : settings-dictionary (option, value) pairs,
      plugin:<pluginname>   : settings-dictionary (option, value) pairs,
      ...
  }


  base.ini                          *----------->mount.ini (per app instance)
  --------                          |            ----------------------------
                                    |      
  [DEFAULT] ------------------------|-----* *--- [DEFAULT]
  <option> = <value>                |     | |    <option> = <value>
  ...                               |     | |    ...
                                    |     | |
  [pluggdapps]                      |     | | *- [plugin:<pluginname>]
  <option> = <value>                |     | | |  <option> = <value>
  ...                               |     | | |  ...
                                    |     | | |
  [webmounts] ---------------------*|     | | |  [plugin:...]
  <appname> = (<type>, <value>)    ||     | | |  ...
  <appname> = (<type>, <value>, mountini) | | |
  ...                              |      | | |         Default Settings
                                   |      | | |         ----------------
  [webapp:<appname>] ------------------*  **|-|---------- global_default = {
  <option> = <value>               |   |  | | |           }
  ...                              |   |  | | |          
                                   |   |  | | |       *---webapp_configdict = {
  [webapp:...]                     |   |  | | |       |   }
  ...                              |   |  | | |       |   ...
                                   |   |  | | *       |   
  [plugin:<pluginname>] ---------------|--|-|-*-----* | *-plugin_configdict = {
  <option> = <value>               |   |  | |       | | | }
  ...                              |   |  | |       | | | ...
                                   |   |  | |       | | |
  [plugin:...]                     |   |  | |       | | |
  ...                              |   |  | |       | | |
                                   |   |  | |       | | |
  Settings                         |   |  | |       | | |
  --------                         |   |  | |       | | |
   { 'pluggdapps'    :<sett>,  <---|---|--* |       | | |
     'webmounts'     :<sett>,  <---*   |    |       | | |
     'plugin:<name>' :<sett>,          |    |       | | |
     ...                               |    |       | | |
     ('webapp:<appname>',: <instsett>, **---*       | | |
      type, val, conf)                 |            | | |
     ...                               |            | | |
   }                                   *            | | |
                                      **------------|-* |
                                      |             |   |
                                      V             *--**
             { 'webapp:<appname>'   : <settings>,       |
               'plugin:<pluginname> : <settings>, <-----*
               ...                                      
             }                                           
                                                         
Special sections:
-----------------

Special sections, base.ini can have the following special sections,
[DEFAULT], [pluggdapps] and [webmounts]. All other section names are to be
prefixed with either "plugin:<pluginname>".
  
  * [DEFAULT] special section, settings that are applicable to all configuration
    sections including plugins, refered configuration files.
  
  * [pluggdapps] special section, settings that are applicable to pluggdapps
    platform typically handled by :class:`Pluggdapps`.
  
  * [webmounts] special section, is specific to web-framework that is built on
    top of pluggdapps system. Provides configuration settings on how to
    mount web-applications on web-url. Typically handled by :class:`WebApps`.
  
Notes:
------

  * base.ini file acts as the master configuration file and can refer to other
    configuration file per application available under pluggdapps.
  

Mounting applications:
----------------------

Configured under [webmounts] special section in master ini file.

  * instance wise configuration file. Every mounted application's instance can
    refer to a configuration file that pertain to that instance alone. Such
    files can have configuration sections for that application and all other 
    plugins.
  
  * An application is nothing but a plugin implementing :class:`IApplication`
    interface specification.
  



"""

from   configparser          import SafeConfigParser

from   pluggdapps.const      import MOUNT_SUBDOMAIN, MOUNT_SCRIPT
from   pluggdapps.plugin     import Singleton, ISettings, applications, \
                                    query_plugin, query_plugins, IWebApp
from   pluggdapps.interfaces import IRequest, IResponse
import pluggdapps.utils      as h


def DEFAULT():
    """Global default settings that are applicable to all plugins and
    sections, and can be overriden by base configuration file's 'DEFAULT'
    section."""
    sett = h.ConfigDict()
    sett.__doc__ = "Global configuration settings with system-wide scope."
    sett['debug']  = {
        'default'  : False,
        'types'    : (bool,),
        'help'     : "Boot and run pluggdapps system in debug mode.",
        'webconfig': False,
    }
    return sett


def normalize_defaults( sett ):
    """Normalize settings for [DEFAULT]."""
    sett['debug'] = h.asbool( sett.get('debug', False) )
    return sett


def pluggdapps_defaultsett():
    """Default settings for [pluggdapps] section in ini file."""
    sett = h.ConfigDict()
    return sett


def normalize_pluggdapps( sett ):
    """Normalize settings for [pluggdapps]."""
    return sett


def defaultsettings():
    """By now it is expected that all interface specs and plugin definitions
    would have been loaded by loading packages implementing them and
    pluggdapps' plugin meta-classing. This function will collect their
    default settings and return them as settings dictionary,

        { "plugin:<pluginname>" : default_settings,
           ...
        }

    """
    from pluggdapps.plugin import PluginMeta

    # Default settings for plugins.
    plugindefaults = {}

    # Fetch all the default-settings for loaded plugins using `ISettings`
    # interface. Plugin inheriting from other plugins will override its
    # base's default_settings() in cls.mro() order.
    for info in PluginMeta._pluginmap.values() :
        name = info['name']
        bases = reversed( info['cls'].mro() )
        sett = {}
        [sett.update( dict( b.default_settings().items() )) for b in bases]
        plugindefaults[ plugin2sec(name) ] = sett

    return plugindefaults


class Pluggdapps( object ):
    """Platform class tying together pluggdapps platform. The platform starts
    with the boot() method call (which is a classmethod)."""

    port = None
    """If the platform is booted via an erlang port interface this attribute
    will be set to :class:`Port` object."""

    inifile = None
    """Master Configuration file, absolute location."""

    settings = {}
    """Default settings from plugins overriden by settings from master
    configuration file."""

    def __init__( self, *args, **kwargs ):
        self.port = kwargs.pop( 'port', False )

    @classmethod
    def boot( cls, baseini, *args, **kwargs ):
        """Boot sequence
        * Boot platform using master configuration file, refer module

        Return a new instance of this class object.
        """
        pa = cls( *args, **kwargs )
        pa.inifile = baseini
        pa.settings = pa.loadsettings( baseini )
        return pa

    def loadsettings( self, inifile ):
        """Load `baseini` and instance-wise ini files (for each web-app) and
        return them as dictionary of app settings."""
        from pluggdapps.plugin import plugin_info

        SPECIAL_SECS = [ 'pluggdapps' ]
        plugindefaults = defaultsettings()

        # Override plugin defaults for each application with configuration
        # from its ini-file
        settings = self.loadini( baseini, plugindefaults )

        # Normalize special sections settings
        settings['pluggdapps'] = normalize_pluggdapps( settings['pluggdapps'] )

        # Normalize plugins
        for sec, sett in settings.items()[:] :
            if sec in SPECIAL_SECS : continue
            if not sec.startswith( 'plugin:' ) : continue

            cls = plugin_info( sec2plugin(sec) )['cls']
            for b in reversed( cls.mro() ) :
                if hasattr(b, 'normalize_settings') :
                    sett = b.normalize_settings( sett )
            settings[ sec ] = sett

        return settings


    def loadini( self, baseini, plugindefaults ):
        """Parse master ini configuration file `baseini` and ini files refered by
        `baseini`. Construct a dictionary of settings for all sections and
        plugins."""
        from pluggdapps.plugin import pluginnames

        # Initialize return data.
        settings = {}

        # context for parsing ini files.
        _vars = { 'here' : dirname(baseini) }

        # Read master ini file.
        cp = configparser.SafeConfigParser()
        cp.read( baseini )

        # Global defaults
        defaultsett1 = normalize_defaults( dict( DEFAULT().items() ))
        # [DEFAULT] overriding global def.
        defaultsett2 = normalize_defaults( cp.defaults() )

        # Package defaults for `pluggdapps` special section. And override them
        # with [DEFAULT] settings and then with settings from master ini file's
        # [pluggdapps] section.
        sec_pluggdapps = h.mergedict( defaultsett1, 
                                      dict( pluggdapps_defaultsett().items() ),
                                      defaultsett2 )
        if cp.has_section('pluggdapps') :
            sec_pluggdapps.update( dict( cp.items( 'pluggdapps', vars=_vars )))
        settings['pluggdapps'] = sec_pluggdapps

        settings['DEFAULTS'] = h.mergedict( defaultsett1, defaultsett2 )

        # Override plugin's package default settings with [DEFAULT] settings.
        for pluginsec, sett in plugindefaults.items() :
            s = h.mergedict( defaultsett1, sett, defaultsett2 )
            if cp.has_section( pluginsec ) :
                s.update( dict( cp.items( pluginsec, vars=_vars )))
            settings[ pluginsec ] = s

        return settings

    #---- platform logging

    def logerror( self, formatstr, values ):
        if self.port :
            Port.logerror( self, formatstr, values )
        else :
            formatstr = formatstr.replace( '~', '%' ) if values else formatstr
            print( formatstr % values )

    def logwarn( self, formatstr, values ):
        if self.port :
            Port.logerror( self, formatstr, values )
        else :
            formatstr = formatstr.replace( '~', '%' ) if values else formatstr
            print( formatstr % values )

    def loginfo( self, formatstr, values ):
        if self.port :
            Port.logerror( self, formatstr, values )
        else :
            formatstr = formatstr.replace( '~', '%' ) if values else formatstr
            print( formatstr % values )

    def logwarning( self, formatstr, values ):
        if self.port :
            Port.logerror( self, formatstr, values )
        else :
            formatstr = formatstr.replace( '~', '%' ) if values else formatstr
            print( formatstr % values )



class Webapps( Pluggdapps ):
    """For web-applications."""

    m_subdomains = {}
    """Mapping urls to applications based on subdomain."""

    m_scripts = {}
    """Mapping url to application based on script."""

    webapps = {}
    """Instances of :class:`WebApp` plugin."""

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )

    @classmethod
    def boot( cls, baseini, *args, **kwargs ):
        """Boot sequence
        * Boot platform using master configuration file, refer module
          `pluggdapps.config`.

        Return a new instance of this class object.
        """
        pa = super().boot( baseini, *args, **kwargs )
        pa.m_subdomains = {}    # Instance attribute
        pa.m_scripts = {}       # Instance attribute
        pa.webapps = {}         # Instance attribute

        appsettings = self.webmounts()
        # Mount webapp instances for subdomains and scripts.
        for instkey, appsett in appsettings.items() :
            appsec, t, mountname, config = instkey

            # Instantiate the IWebAPP plugin here for each `instkey`
            appname = h.sec2plugin( appsec )
            webapp = query_plugin( pa, instkey, IWebApp, appname, appsett )
            webapp.instkey = instkey
            webapp.pa = pa
            webapp.subdomain, webapp.script = None, None

            # Resolution mapping for web-applications
            if t == MOUNT_SUBDOMAIN :
                pa.m_subdomains.setdefault( mountname, webapp )
                webapp.subdomain = mountname
            elif t == MOUNT_SCRIPT :
                pa.m_scripts.setdefault( mountname, webapp )
                webapp.script = mountname
        return pa

    def webmounts( self ):
        """Create application wise settings. If special section webmounts is
        present, parse referred configuration files."""
        from pluggdapps.plugin import pluginnames, applications

        SPECIAL_SECS = [ 'pluggdapps' ]
        settings = self.settings

        # Fetch special section [webmounts]. And override them with [DEFAULT]
        # settings.
        cp = configparser.SafeConfigParser()
        cp.read( self.inifile )
        if cp.has_section('webmounts') :
            webmounts = cp.items( 'webmounts', vars=_vars )
        else :
            webmounts = []
        settings['webmounts'] = dict(webmounts)

        # Parse mount configuration.
        appsecs = list( map( plugin2sec, applications() ))
        defaultmounts = appsecs[:]
        for (name, val) in webmounts :
            appsec = plugin2sec( name )
            if appsec not in appsecs : continue

            # Parse mount values and validate them.
            y = [ x.strip() for x in val.split(',') ]
            try :
                t, mountname, instconfig = y
            except :
                try :
                    t, mountname, instconfig = y + [None]
                except :
                    raise Exception("Invalid mount configuration %r" % val)

            if t not in MOUNT_TYPES :
                err = "%r for %r is not a valid mount type" % (t, name)
                raise Exception( err )
            
            webmounts.append( (appsec,t,mountname,instconfig) )
            defaultmounts.pop( appsec )

        # Configure default mount points for remaining applications.
        [ webmounts.append(
            (appsec, MOUNT_SCRIPT, "/"+h.sec2plugin(appsec), None)
          ) for appsec in defaultmounts ]

        # Load application configuration from instance configuration file.
        appsettings = {}
        for appsec, t, mountname, instconfig in webmounts :
            appsett = deepcopy( settings )
            if instconfig :
                self.loadinstance( appsett, instconfig )
            appsettings[ (appsec,t,mountname,instconfig) ] = appsett
        return appsettings

    def loadinstance( self, appsett, instanceini ):
        """Load configuration settings for a web application's instance."""
        _vars = { 'here' : dirname(instanceini) }
        cp = configparser.SafeConfigParser()
        cp.read( instanceini )

        # Update appsett with [DEFAULT] section of instanceini
        defaultsett = dict( cp.defaults() )
        appsett['DEFAULT'].update( defaultsett )
        [ sett.update( defaultsett ) for key, sett in appsett.items() ]

        # Update plugin sections in appsett from instanceini
        [ appsett[sec].update( dict( cp.items( sec, vars=_vars )))
          for sec in cp.sections() if sec.startswith( 'plugin:' ) ]


    def bootapps( self ):
        """Boot all loaded application. Web-Apps are loaded when the
        system is booted via boot() call. Apps are booted only when an
        explicit call is made to this method."""
        global webapps
        appnames = []
        for appname in sorted( webapps ) :
            self.loginfo( "Booting application %r ..." % appname, [] )
            webapps[appname].onboot()
            appnames.append( appname )
        return appnames

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

    def makerequest( self, conn, address, startline, headers, body ):
        global webapps
        # Parse request start-line
        method, uri, version = h.parse_startline( startline )
        uriparts = h.parse_url( uri, headers.get('Host', None) )

        # Resolve application
        (typ, key, appname) = self.appresolve( uriparts, headers, body )
        webapp = webapps[ appname ]

        # IRequest plugin
        request = query_plugin(
                        webapp, IRequest, webapp['irequest'], conn, address, 
                        method, uri, uriparts, version, headers, body )
        response = query_plugin( webapp, IResponse, webapp['iresponse'], self )
        request.response = response

        return request

    def baseurl( self, request, appname=None, scheme=None, auth=False,
                 hostname=None, port=None ):
        """Construct the base URL for request. If `appname` is supplied and
        different from request's app, then base-url will be computed for the
        application `appname`.
        Key word arguments can be used to override the computed valued."""
        global webapps
        webapp, uriparts = request.webapp, request.uriparts
        if appname != pluginname(webapp.appname): # base_url for a different app
            webapp = webapps[ appname ]
            if request.webapp.subdomain :   # strip off this app's subdomain
                apphost = uriparts['hostname'][len(request.webapp.subdomain)+1:]
            else :                      # else, use the hostname as it is
                apphost = uriparts['hostname']
            if webapp.subdomain :
                apphost = webapp.subdomain + '.' + apphost
            app_script = webapp.appscript  # It might or might not be empty
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
            app_port = h.port_for_scheme( scheme, uriparts['port'] )
            url += (':' + app_port) if app_port else ''
        # script
        uri += app_script

        return url

    def shutdown( self ):
        global webapps
        for appname in sorted( webapps ) :
            infostr = "Shutting down application %r ..." % appname
            self.loginfo( infostr, [] )
            webapps[appname].shutdown()


    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings


def appkey( appname ):
    rc = []
    for instkey, v in settings.items() :
        if not isinstance( instkey, tuple ) : continue
        appsec, t, v, config = instkey
        if h.sec2plugin( appsec ) == appname :
            rc.append( instkey )
    return rc


def platform_logs( f ) :
    msg = "%s interfaces defined and %s plugins loaded" % (
           len(PluginMeta._interfmap), len(PluginMeta._pluginmap) )
    print( msg, file=f )
    print( "%s applications loaded" % len(applications()), file=f ) 
    print( "%s pluggdapps packages loaded" % len(pluggdapps.packages), file=f )


def mount_logs( f ):
    global webapps
    for appname in sorted( webapps ) :
        mount = m_subdomains.get( appname, None )
        if mount :
            print( "%r mounted on subdomain %r" % (appname, mount), file=f )
        else :
            mount = m_scripts.get( appname, None )
            print( "%r mounted on scripts %r" % (appname, mount), file=f )

