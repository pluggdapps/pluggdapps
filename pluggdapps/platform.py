# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

"""
Pluggdapps platform:
--------------------

Parse configuration settings from various sources and aggregates them for
plugin instantiation.

Provides methods for logging error / warning messages.

Configuration:
--------------

Platform's boot method expect an ini-file regarded as master configuration
file. Settings in this master configuration file will override package default
settings for plugins and other sections.

Any configuration section not prefixed with 'plugin:' is considered as special
section, which are explained further below.

Master configuration file can refer to other configuration file.
  

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

Special sections:
-----------------

[DEFAULT] special section, settings that are applicable to all
configuration sections including plugins and refered configuration files.

[pluggdapps] special section, settings that are applicable to pluggdapps
platform typically handled by :class:`Pluggdapps`.

[mountloc] special section, is specific to web-framework (explained below)
that is built on top of pluggdapps system. Provides configuration settings on
how to mount web-applications on web-url. Typically handled by
:class:`Webapps`.
  
Web-application platform:
-------------------------

Can host any number web-application, and/or instance of same web-application,
in a single python environment. Every web-application is a plugin implementing
:class:`IWebApp` interface.

Web-applications can be mounted, hosted, on a netlocation and script-path.
This is configured under [mountloc] special section. While mounting
web-applications under [mountloc] additional configuration files, exclusive
to the scope of mounted webapp, can be referred as well.

:class:`Webapps` provides the necessary logic. 

Example [mountloc] section

  [mountloc]
  pluggdapps.com/issues = <appname>, <ini-file>
  tayra.pluggdapps.com/issues = <appname>, <ini-file>
  tayra.pluggdapps.com/source = <appname>, <ini-file>

"""

from   configparser          import SafeConfigParser
from   os.path               import dirname, isfile
from   copy                  import deepcopy

from   pluggdapps.const      import SPECIAL_SECS, URLSEP
from   pluggdapps.interfaces import IWebApp
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
    sett.__doc__ = "Pluggdapps platform settings."
    sett['scheme'] = {
        'default'  : 'http',
        'types'    : (str,),
        'help'     : "HTTP Scheme to use, either `http` or `https`."
    }
    sett['host'] = {
        'default'  : 'localhost',
        'types'    : (str,),
        'help'     : "Top level domain name of host, web server, which "
                     "receives the request."
    }
    sett['port'] = {
        'default' : 8080,
        'types'   : (int,),
        'help'    : "Port addres to bind the http server."
    }
    return sett


def normalize_pluggdapps( sett ):
    """Normalize settings for [pluggdapps]."""
    sett['port'] = h.asint( sett['port'] )
    return sett


class Pluggdapps( object ):
    """Platform class tying together pluggdapps platform. The platform starts
    with the boot() method call (which is a classmethod)."""

    inifile = None
    """Master Configuration file, absolute location."""

    settings = {}
    """Default settings from plugins overriden by settings from master
    configuration file and other backend stores, if any."""

    erlport = None
    """If the platform is booted via an erlang port interface this attribute
    will be set to :class:`ErlPort` object."""

    def __init__( self, erlport=None ):
        self.erlport = erlport

    #---- Overridable methods.

    @classmethod
    def boot( cls, baseini, *args, **kwargs ):
        """Boot the platform using master configuration file `baseini`.

        Return a new instance of this class object. This is the only way to
        create a platform instance.
        """
        pa = cls( *args, **kwargs )
        pa.inifile = baseini
        pa.settings = pa.loadsettings( baseini )
        return pa

    def start( self ):
        """Expected to be called after boot(). Start pluggdapps."""
        pass

    def shutdown( self ):
        """Reverse of start() method."""
        pass

    def masterinit( self, plugin, *args, **kwargs ):
        """Call back function during plugin instantiation, from
        :class:`PluginMeta` plugin.
        """
        from pluggdapps.plugin import pluginname
        plugin._settngx.update( 
                self.settings[ h.plugin2sec( pluginname(plugin)) ])
        plugin.pa = self

        # Plugin settings
        plugin._settngx.update( kwargs.pop( 'settings', {} ))

        plugin.query_plugins = hitch( plugin, plugin.__class__,
                                      Pluggdapps.query_plugins, self )
        plugin.query_plugin  = hitch( plugin, plugin.__class__,
                                      Pluggdapps.query_plugin, self )
        return args, kwargs

    #---- Internal methods.

    def loadsettings( self, inifile ):
        """Load `inifile` and override the default settings with inifile's
        configuration.

        Return them as dictionary of app settings."""

        SPECIAL_SECS = [ 'pluggdapps' ]
        defaults = self.defaultsettings()
        # Override plugin defaults with configuration from ini-file(s)
        return self.loadini( inifile, defaults )


    def loadini( self, baseini, defaultsett ):
        """Parse master ini configuration file `baseini` and ini files refered
        by `baseini`. Construct a dictionary of settings for special sections
        and plugin sections."""
        from pluggdapps.plugin import pluginnames, plugin_info

        # Initialize return dictionary.
        settings = {}

        # context for parsing ini files.
        _vars = { 'here' : dirname(baseini) }

        # Read master ini file.
        cp = SafeConfigParser()
        cp.read( baseini )

        # [DEFAULT] overriding global def.
        s = deepcopy( defaultsett['DEFAULT'] )
        s.update( dict( cp.defaults() ))
        settings['DEFAULT'] = normalize_defaults( s )

        # [pluggdapps]
        s = deepcopy( defaultsett['pluggdapps'] )
        if cp.has_section('pluggdapps') :
            s.update( dict( cp.items( 'pluggdapps', raw=True, vars=_vars )))
            settings['pluggdapps'] = normalize_pluggdapps( s )

        # Override plugin's package default settings with [DEFAULT] settings.
        for pluginsec, sett in defaultsett.items() :
            if not pluginsec.startswith( 'plugin:' ) : continue
            sett = h.mergedict( sett, settings['DEFAULT'] )
            if cp.has_section( pluginsec ) :
                sett.update( dict( cp.items( pluginsec, raw=True, vars=_vars )))
            cls = plugin_info( h.sec2plugin( pluginsec ) )['cls']
            for b in reversed( cls.mro() ) :
                if hasattr( b, 'normalize_settings' ) :
                    sett = b.normalize_settings( sett )
            settings[ pluginsec ] = sett

        return settings


    def defaultsettings( self ):
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
        default = normalize_defaults( dict( DEFAULT().items() ))
        defaultsett = { 'DEFAULT'    : deepcopy(default) }

        defaultsett['pluggdapps'] = deepcopy(default)
        defaultsett['pluggdapps'].update( 
                normalize_pluggdapps( dict( pluggdapps_defaultsett().items() )))

        # Fetch all the default-settings for loaded plugins using `ISettings`
        # interface. Plugin inheriting from other plugins will override its
        # base's default_settings() in cls.mro() order.
        for info in PluginMeta._pluginmap.values() :
            name = info['name']
            bases = reversed( info['cls'].mro() )
            sett = deepcopy( default )
            [ sett.update( dict( b.default_settings().items() )) 
              for b in bases if hasattr(b, 'default_settings') ]
            defaultsett[ h.plugin2sec(name) ] = sett

        return defaultsett


    #---- Query APIs

    @staticmethod
    def query_plugins( pa, interface, *args, **kwargs ):
        """Use this API to query for plugins using the `interface` class it
        implements. Positional and keyword arguments will be used to instantiate
        the plugin object.

        `interface`,
            :class:`Interface`

        If ``settings`` key-word argument is present, it will be used to
        override default plugin settings.

        Returns a list of plugin instance implementing `interface`
        """
        from pluggdapps.plugin import PluginMeta
        return [ pcls( pa, *args, **kwargs )
                 for pcls in PluginMeta._implementers[interface].values() ]

    @staticmethod
    def query_plugin( pa, interface, name, *args, **kwargs ):
        """Same as queryPlugins, but returns a single plugin instance as opposed
        an entire list. `name` will be used to identify that plugin.
        Positional and keyword arguments will be used to instantiate the plugin
        object.

        `interface`,
            :class:`Interface`

        If ``settings`` key-word argument is present, it will be used to
        override default plugin settings.

        Return a single Plugin instance.
        """
        from pluggdapps.plugin import PluginMeta, pluginname
        cls = PluginMeta._implementers[ interface ][ pluginname(name) ]
        return cls( pa, *args, **kwargs )


    #---- platform logging

    def loginfo( self, formatstr, values=[] ):
        self.erlport.loginfo(formatstr, values) \
                if self.erlport else print(formatstr)

    def logwarn( self, formatstr, values=[] ):
        formatstr = 'WARN: ' + formatstr
        self.erlport.logwarn(formatstr, values) \
                if self.erlport else print(formatstr)

    def logerror( self, formatstr, values=[] ):
        formatstr = 'ERROR: ' + formatstr
        self.erlport.logerror(formatstr, values) \
                if self.erlport else print(formatstr)


class Webapps( Pluggdapps ):
    """Configuration for web-application plugins."""

    webapps = {}
    """Instances of :class:`WebApp` plugin."""

    appurls = {}
    """A dictionary map of webapp's instkey and its base-url -  scheme, netloc,
    scriptname."""

    app_resolve_cache = {}
    """A dictionary map of (netloc, script-path) to Web-application object."""

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )

    #---- Overridable methods

    @classmethod
    def boot( cls, baseini, *args, **kwargs ):
        """Boot sequence
        Return a new instance of this class object.
        """
        pa = super().boot( baseini, *args, **kwargs )
        pa.webapps = {}
        pa.appurls = {}

        appsettings = pa.mountapps()

        # Mount webapp instances for subdomains and scripts.
        for instkey, appsett in appsettings.items() :
            appsec, netpath, config = instkey

            # Instantiate the IWebAPP plugin here for each `instkey`
            appname = h.sec2plugin( appsec )
            webapp = pa.query_plugin( pa, instkey, IWebApp, appname, appsett )
            webapp.appsetting = appsett
            webapp.instkey, webapp.netpath = instkey, None
            pa.webapps[ instkey ] = webapp
            pa.appurls[ instkey ] = webapp.baseurl = pa.make_appurl( instkey )

            pa.app_resolve_cache[ h.parse_netpath( netpath ) ] = webapp

            # Resolution mapping for web-applications
            webapp.netpath = netpath

        return pa

    def start( self ):
        """Boot all loaded application. Web-Apps are loaded when the
        system is booted via boot() call. Apps are booted only when an
        explicit call is made to this method."""
        super().start()
        appnames = []
        for instkey, webapp in self.webapps.items() :
            appsec, netpath, configini = instkey
            self.loginfo( "Booting application %r ..." % netpath )
            webapp.startapp()
            appnames.append( h.sec2plugin( appsec ))
        return appnames

    def shutdown( self ):
        """Reverse of start() method."""
        for instkey, webapp in self.webapps.items() :
            self.loginfo( "Shutting down application %r ..." % appname )
            webapp.shutdown()
        super().shutdown()

    def masterinit( self, plugin, webapp, *args, **kwargs ):
        """Call back function during plugin instantiation, from
        :class:`PluginMeta` plugin.
        """
        from pluggdapps.plugin import pluginname
        from pluggdapps.web.webapp import WebApp

        if isinstance( plugin, WebApp ) : # Ought to be IWebApp plugin
            appsec, t, mountname, config = webapp
            plugin._settngx.update( args[0][ appsec ] )
            plugin.webapp = plugin
            args = args[1:]

        elif webapp :                   # Not a IWebApp plugin
            plugin._settngx.update(
                webapp.appsetting[ h.plugin2sec( pluginname( plugin )) ]
            )
            plugin.webapp = webapp

        else :                          # plugin not under a webapp
            plugin._settngx.update(
                    self.settings[ h.plugin2sec( pluginname( plugin )) ]
            )
            plugin.webapp = None

        plugin.pa = self

        plugin.query_plugins = hitch( 
            plugin, plugin.__class__, Webapps.query_plugins,
            self, plugin.webapp )
        plugin.query_plugin = hitch(
            plugin, plugin.__class__, Webapps.query_plugin,
            self, plugin.webapp )

        # Plugin settings
        plugin._settngx.update( kwargs.pop( 'settings', {} ))
        return args, kwargs

    #---- Internal methods

    def mountapps( self ):
        """Create application wise settings, using special section
        [mountloc], if any. Also parse referred configuration files."""
        from pluggdapps.plugin import pluginnames, applications

        settings = self.settings

        # context for parsing ini files.
        _vars = { 'here' : dirname(self.inifile) }


        # Fetch special section [mountloc]. And override them with [DEFAULT]
        # settings.
        cp = SafeConfigParser()
        cp.read( self.inifile )
        if cp.has_section('mountloc') :
            mountloc = cp.items( 'mountloc', vars=_vars )
        else :
            mountloc = []
        settings['mountloc'] = dict( mountloc )

        # Parse mount configuration.
        
        appsecs = list( map( h.plugin2sec, applications() ))
        mountls = []
        _skipopts = list(_vars.keys()) + list(settings['DEFAULT'].keys())
        for netpath, mounton in mountloc :
            if netpath in _skipopts : continue

            parts = mounton.split(',', 1)
            appname = parts.pop(0).strip()
            configini = parts.pop(0).strip() if parts else None
            appsec = h.plugin2sec( appname )

            if appsec not in appsecs :
                raise Exception("%r application not found." % appname )
            if not isfile( configini ) :
                raise Exception("configuration file %r not present"%configini )

            mountls.append( (appsec,netpath,instconfig) )

        # Load application configuration from instance configuration file.
        appsettings = {}
        for appsec, netpath, instconfig in mountls :
            appsett = deepcopy( settings )
            [ appsett.pop(k) for k in SPECIAL_SECS ]
            if instconfig :
                self.loadinstance( appsett, instconfig )
            appsettings[ (appsec,netpath,instconfig) ] = appsett
        return appsettings


    def loadinstance( self, appsett, instanceini ):
        """Load configuration settings for a web application's instance."""
        from pluggdapps.plugin import plugin_info
        _vars = { 'here' : dirname(instanceini) }
        cp = SafeConfigParser()
        cp.read( instanceini )

        # Update appsett with [DEFAULT] section of instanceini
        defaultsett = dict( cp.defaults() )
        appsett['DEFAULT'].update( defaultsett )
        appsett['DEFAULT'] = normalize_defaults( appsett['DEFAULT'] )
        [ sett.update( appsett['DEFAULT'] ) for key, sett in appsett.items() ]

        # Update plugin sections in appsett from instanceini
        for sec in cp.sections() :
            if not sec.startswith( 'plugin:' ) : continue
            sett = dict( cp.items( sec, raw=True, vars=_vars ))
            appsett[sec].update( sett )
            cls = plugin_info( h.sec2plugin( sec ) )['cls']
            for b in reversed( cls.mro() ) :
                if hasattr( b, 'normalize_settings' ) :
                    appsett[sec] = b.normalize_settings( appsett[sec] )


    def make_appurl( self, instkey ):
        """Compute the base url for application specified by `instkey` which
        is a tuple of,
            ( appsec, mount-type, mount-name, configfile)

        Return the base-url as byte-string.
        """
        host = self.settings['pluggdapps']['host']
        port = self.settings['pluggdapps']['port']
        scheme = self.settings['pluggdapps']['scheme']
        appsec, netpath, config = instkey
        netloc, script = h.parse_netpath( netpath )
        if not netloc.endswith( host ) :
            raise Exception(
                "Mount location's netloc does not match with host config." )

        # Prefix scheme
        appurl = scheme + '://' + netloc

        # prefix port
        if port :
            if (scheme, port) in [ ('http', 80), ('https', 443) ] :
                port = ''
            else :
                port = str(port)
            appurl += ':' + port

        # Prefix SCRIPT-NAME, mountname is already prefixed with URLSEP
        appurl += script

        return appurl

    #---- Query APIs

    @staticmethod
    def query_plugins( pa, webapp, interface, *args, **kwargs ):
        """Use this API to query for plugins using the `interface` class it
        implements. Positional and keyword arguments will be used to instantiate
        the plugin object.

        `interface`,
            :class:`Interface`

        If ``settings`` key-word argument is present, it will be used to
        override default plugin settings.

        Returns a list of plugin instance implementing `interface`
        """
        from pluggdapps.plugin import PluginMeta
        return [ pcls( pa, webapp, *args, **kwargs )
                 for pcls in PluginMeta._implementers[interface].values() ]

    @staticmethod
    def query_plugin( pa, webapp, interface, name, *args, **kwargs ):
        """Same as queryPlugins, but returns a single plugin instance as opposed
        an entire list. `name` will be used to identify that plugin.
        Positional and keyword arguments will be used to instantiate the plugin
        object.

        `interface`,
            :class:`Interface`

        If ``settings`` key-word argument is present, it will be used to
        override default plugin settings.

        Return a single Plugin instance.
        """
        from pluggdapps.plugin import PluginMeta, pluginname
        cls = PluginMeta._implementers[ interface ][ pluginname(name) ]
        return cls( pa, webapp, *args, **kwargs )



    #---- APIs related to hosting multiple-applications.

    def resolveapp( self, uri, hdrs ):
        """Resolve application for `request`. Return a tuple of,
            (uriparts, mountedat)
            
        `uriparts`
            dictionary of URL parts 
        `mountedat`
            (type, mountname, webapp-instance)
        """
        uriparts = h.parse_url( uri, host=hdrs.get('host', None) )
        h = uriparts['hostname']
        netloc = h[3:] if h.startswith('www') else h
        for key, webapp in self.app_resolve_cache.items() :
            netloc, script = key
            if ( netloc == uriparts['hostname'] and 
                    uriparts['path'].startswith( script ) ):
                uriparts['script'] = script
                uriparts['path'] = uriparts['path'][len(script):]
                return uriparts, webapp
        return uriparts, None

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings


def hitch( obj, cls, function, *args, **kwargs ) :
    """Hitch a function with a different object and different set of
    arguments."""
    def fnhitched( self, *a, **kw ) :
        kwargs.update( kw )
        return function( *(args+a), **kwargs )
    return fnhitched.__get__( obj, cls )


