# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""
Parse configuration settings from various sources (at present ini-files are
supported), aggregate them, make them avialable on plugins instances. It also
provides methods for logging error / warning messages.

Configuration:
--------------

Platform's boot method expect an ini-file regarded as master configuration
file. Settings in this master configuration file will override package default
settings for plugins and other special sections. Any configuration section not
prefixed with **plugin:** is considered as special section, which are explained
further below. Master configuration file can refer to other configuration file.
  
An example master configuration file,::

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

**[DEFAULT]** special section, settings that are applicable to all
configuration sections including plugins and refered configuration files.
Semantic meaning of [DEFAULT] section is same as described by ``configparser``
module from stdlib.

**[pluggdapps]** special section, settings that are applicable to pluggdapps
platform typically handled by :class:`Pluggdapps`.

**[mountloc]** special section, is specific to web-framework (explained below)
that is built on top of pluggdapps component architecture. Provides 
configuration settings on how to mount web-applications on web-url. Typically
handled by :class:`Webapps`.
  
Web-application platform:
-------------------------

Implemented by :class:`Webapps` class (which derives from base platform class
:class:`Pluggdapps`), it can host any number web-application, and/or instance
of same web-application, in a single python environment. Every web-application
is a plugin implementing :class:`pluggdapps.interfaces.IWebApp` interface.
When plugins are instantiated by a webapp plugin, either directly or
indirectly, the instantiated plugins are automatically supplied with
**.webapp** attribute.

Web-applications can be mounted, hosted, on a netlocation and script-path
(collectively called as ``netpath``). This is configured under **[mountloc]**
special section. While mounting web-applications under [mountloc] additional 
configuration files can be referred.

Example [mountloc] section,::

  [mountloc]
  pluggdapps.com/issues = <appname>, <ini-file>
  tayra.pluggdapps.com/issues = <appname>, <ini-file>
  tayra.pluggdapps.com/source = <appname>, <ini-file>

The referred configuration files are exclusive to the scope of the mounted
application, and shall not contain any special sections, except `[DEFAULT]`,
unless otherwise explicitly mentioned. When a plugin is instantiated in the
context of a web-application, configuration settings from application-ini-file
will override settings from the master-ini-file.

Finally the platform can be started like,::

  pa = Webapps.boot( args.config )

where ``args.config`` locates the master-ini file
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
    section. Semantic meaning of [DEFAULT] section is same as described by
    ``configparser`` module from stdlib."""
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
    """Normalize settings for [DEFAULT] special section."""
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
    sett['logging.output'] = {
        'default' : 'console',
        'types'   : (str,),
        'help'    : "Comma separated value of names to log messages. Supported "
                    "names are `console`, `file`."
    }
    sett['logging.file'] = {
        'default' : '',
        'types'   : (str,),
        'help'    : "File name to log messages. Make sure to add `file` in "
                    "`logging` parameter."
    }
    return sett


def normalize_pluggdapps( sett ):
    """Normalize settings for [pluggdapps] special section."""
    sett['port'] = h.asint( sett['port'] )
    if isinstance( sett['logging.output'], str ):
        sett['logging.output'] = h.parsecsv( sett['logging.output'] )
    return sett


class Pluggdapps( object ):
    """Platform class tying together pluggdapps platform, component
    architecture and configuration system. Do not instantiate this class
    directly, instead use the boot() method call (which is a classmethod) to
    start the platform."""

    inifile = None
    """Master Configuration file, absolute location."""

    settings = {}
    """Default settings for plugins, gathered from plugin-default settings,
    master configuration file and other backend stores, if any."""

    def __init__( self, erlport=None ):
        self.erlport = erlport # TODO: Document this once bolted with netscale

    #---- Overridable methods.

    @classmethod
    def boot( cls, baseini, *args, **kwargs ):
        """Boot the platform using master configuration file ``baseini``.  
        Return a new instance of this class object. This is the only way to
        create a platform instance.
        """
        pa = cls( *args, **kwargs )
        pa.inifile = baseini
        pa.settings = pa._loadsettings( baseini )
        # Configure logging
        pa.logsett = h.settingsfor( 'logging.', pa.settings['pluggdapps'] )
        return pa

    def start( self ):
        """Expected to be called after boot(). Start pluggdapps."""
        pass

    def shutdown( self ):
        """Reverse of start() method."""
        pass

    def masterinit( self, plugin, *args, **kwargs ):
        """Call back function during plugin instantiation, from
        :class:`pluggdapps.plugin.PluginMeta` class.

        ``plugin``,
            Instantiated plugin. ``plugin`` is automatically populated with
            configuration settings.

        ``args`` and ``kwargs``,
            are received from query_plugin's ``args`` and ``kwargs``.
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

    def _loadsettings( self, inifile ):
        """Load ``inifile`` and override the default settings with inifile's
        configuration. Return them as dictionary of global settings."""

        SPECIAL_SECS = [ 'pluggdapps' ]
        defaults = self._defaultsettings()
        # Override plugin defaults with configuration from ini-file(s)
        return self._loadini( inifile, defaults )


    def _loadini( self, baseini, defaultsett ):
        """Parse master ini configuration file ``baseini`` and ini files refered
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

    def _defaultsettings( self ):
        """By now it is expected that all interface specs and plugin definitions
        would have been loaded by loading packages implementing them and
        pluggdapps' plugin meta-classing. This function will collect their
        default settings and return them as settings dictionary,::

          { "plugin:<pluginname>" : default_settings,
             ...
          }
        """
        from pluggdapps.plugin import PluginMeta

        # Default settings for plugins.
        default = dict( DEFAULT().items() )
        defaultsett = { 'DEFAULT'    : deepcopy(default) }

        defaultsett['pluggdapps'] = deepcopy(default)
        defaultsett['pluggdapps'].update( 
                        dict( pluggdapps_defaultsett().items() ))

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
        """Use this API to query for plugins using the ``interface`` class it
        implements. Positional and keyword arguments will be used to
        instantiate the plugin object.

        ``pa``,
            Platform object, whose base class is :class:`Pluggdapps`.

        ``interface``,
            :class:`pluggdapps.plugin.Interface` class.

        ``args`` and ``kwargs``,
            Positional and key-word arguments used to instantiate the plugin.

        If `settings` key-word argument is present, it will be used to
        override default plugin settings. Returns a list of plugin instance
        implementing `interface`
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

        ``pa``,
            Platform object, whose base class is :class:`Pluggdapps`.

        ``interface``,
            :class:`pluggdapps.plugin.Interface` class.

        ``name``,
            plugin name, in lower case to query for.

        ``args`` and ``kwargs``,
            Positional and key-word arguments used to instantiate the plugin.

        If ``settings`` key-word argument is present, it will be used to
        override default plugin settings. Return a single Plugin instance.
        """
        from pluggdapps.plugin import PluginMeta, pluginname
        cls = PluginMeta._implementers[ interface ][ pluginname(name) ]
        return cls( pa, *args, **kwargs )


    #---- platform logging

    def loginfo( self, formatstr, values=[] ):
        """Use this method log informational messages. The log messages will
        be formated and handled based on the configuration settings from
        ``[pluggdapps]`` section.
        """
        output, erlport = self.logsett['output'], self.erlport
        if 'cloud' in output and erlport :
            self.erlport.loginfo( formatstr, values )
        if 'file' in output and self.logsett['file'] :
            open( self.logsett['file'], 'a' ).write( formatstr )
        if 'console' in output :
            print( formatstr )

    def logwarn( self, formatstr, values=[] ):
        """Use this method log warning messages. The log messages will
        be formated and handled based on the configuration settings from
        ``[pluggdapps]`` section.
        """
        output, erlport = self.logsett['output'], self.erlport
        formatstr = 'WARN: ' + formatstr
        if 'cloud' in output and erlport :
            self.erlport.logwarn( formatstr, values )
        if 'file' in output and self.logsett['file'] :
            open( self.logsett['file'], 'a' ).write( formatstr )
        if 'console' in output :
            print( colorize( formatstr, color='32' ))

    def logerror( self, formatstr, values=[] ):
        """Use this method log error messages. The log messages will
        be formated and handled based on the configuration settings from
        ``[pluggdapps]`` section.
        """
        output, erlport = self.logsett['output'], self.erlport
        formatstr = 'ERROR: ' + formatstr
        if 'cloud' in output and erlport :
            self.erlport.logerror( formatstr, values )
        if 'file' in output and self.logsett['file'] :
            open( self.logsett['file'], 'a' ).write( formatstr )
        if 'console' in output :
            print( colorize( formatstr, color='31' ))



class Webapps( Pluggdapps ):
    """Provides a web-framework based on a pluggable MVC design pattern. Can
    mount any number of web-application in the same python environment."""

    webapps = {}
    """Dictionay mapping of mount-key and :class:`pluggdapps.web.webapp.WebApp`
    instance, where mount-key is a tuple of appsec, netpath, application-ini"""

    appurls = {}
    """A dictionary map of webapp's instkey and its base-url. The base url 
    consists of scheme, netloc, scriptname."""

    _app_resolve_cache = {}
    """A dictionary map of (netloc, script-path) to Web-application object."""

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )

    #---- Overridable methods

    @classmethod
    def boot( cls, baseini, *args, **kwargs ):
        """Parse ``[mountloc]`` section for application-wise configuration
        settings and return a fresh instance of :class:`Webapps` class.
        """
        pa = super().boot( baseini, *args, **kwargs )
        pa.webapps = {}
        pa.appurls = {}

        appsettings = pa._mountapps()

        # Mount webapp instances for subdomains and scripts.
        for instkey, appsett in appsettings.items() :
            appsec, netpath, config = instkey

            # Instantiate the IWebAPP plugin here for each `instkey`
            appname = h.sec2plugin( appsec )
            webapp = pa.query_plugin( pa, instkey, IWebApp, appname, appsett )
            webapp.appsetting = appsett
            webapp.instkey, webapp.netpath = instkey, None
            pa.webapps[ instkey ] = webapp
            pa.appurls[ instkey ] = webapp.baseurl = pa._make_appurl( instkey )

            
            pa._app_resolve_cache[ h.parse_netpath(netpath) ] = webapp

            # Resolution mapping for web-applications
            webapp.netpath = netpath

        return pa

    def start( self ):
        """Boot all loaded application. Web applicationss are loaded when the
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
        :class:`pluggdapps.plugin.PluginMeta` class.

        ``plugin``,
            Instantiated plugin. ``plugin`` is automatically populated with
            configuration settings and ``webapp`` attribute.

        ``args`` and ``kwargs``,
            are received from query_plugin's ``args`` and ``kwargs``.
        """
        from pluggdapps.plugin import pluginname
        from pluggdapps.web.webapp import WebApp

        if isinstance( plugin, WebApp ) : # Ought to be IWebApp plugin
            appsec, netpath, config = webapp
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

    def _mountapps( self ):
        """Create application wise settings, using special section
        [mountloc], if any. Also parse referred configuration files."""
        from pluggdapps.plugin import pluginnames, webapps

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
        
        appsecs = list( map( h.plugin2sec, webapps() ))
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

            mountls.append( (appsec,netpath,configini) )

        # Load application configuration from instance configuration file.
        appsettings = {}
        for appsec, netpath, instconfig in mountls :
            appsett = deepcopy( settings )
            [ appsett.pop(k) for k in SPECIAL_SECS ]
            if instconfig :
                self._loadinstance( appsett, instconfig )
            appsettings[ (appsec,netpath,instconfig) ] = appsett
        return appsettings


    def _loadinstance( self, appsett, instanceini ):
        """Load configuration settings for a web application's instance."""
        from pluggdapps.plugin import plugin_info
        _vars = { 'here' : dirname(instanceini) }
        cp = SafeConfigParser()
        cp.read( instanceini )

        # Update appsett with [DEFAULT] section of instanceini
        defaultsett = normalize_defaults( dict( cp.defaults() ))
        appsett['DEFAULT'].update( defaultsett )
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


    def _make_appurl( self, instkey ):
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
        """Use this API to query for plugins using the ``interface`` class it
        implements. Positional and keyword arguments will be used to
        instantiate the plugin object.

        ``pa``,
            Platform object, whose base class is :class:`Pluggdapps`.

        ``webapp``,
            Web application object, plugin implementing
            :class:`pluggdapps.interfaces.IWebApp` interface. It is an
            optional argument, which must be passed ``None`` otherwise.

        ``interface``,
            :class:`pluggdapps.plugin.Interface` class.

        ``args`` and ``kwargs``,
            Positional and key-word arguments used to instantiate the plugin.

        If `settings` key-word argument is present, it will be used to
        override default plugin settings. Returns a list of plugin instance
        implementing `interface`
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

        ``pa``,
            Platform object, whose base class is :class:`Pluggdapps`.

        ``webapp``,
            Web application object, plugin implementing
            :class:`pluggdapps.interfaces.IWebApp` interface. It is an
            optional argument, which must be passed ``None` otherwise.

        ``interface``,
            :class:`pluggdapps.plugin.Interface` class.

        ``name``,
            plugin name, in lower case to query for.

        ``args`` and ``kwargs``,
            Positional and key-word arguments used to instantiate the plugin.

        If ``settings`` key-word argument is present, it will be used to
        override default plugin settings. Return a single Plugin instance.
        """
        from pluggdapps.plugin import PluginMeta, pluginname
        cls = PluginMeta._implementers[ interface ][ pluginname(name) ]
        return cls( pa, webapp, *args, **kwargs )



    #---- APIs related to hosting multiple-applications.

    def resolveapp( self, uri, hdrs ):
        """Resolve application for request.

        ``uri``,
            byte-string of request URI.
        ``hdrs``,
            Dictionary of request headers.

        Return a tuple of, (uriparts, mountedat).
            
        ``uriparts``,
            dictionary of URL parts 
        ``mountedat``,
            (type, mountname, webapp-instance)
        """
        uriparts = h.parse_url( uri, host=hdrs.get('host', None) )
        netloc = ( uriparts['host'][3:]
                        if uriparts['host'].startswith('www')
                        else uriparts['host'] )
        for key, webapp in self._app_resolve_cache.items() :
            netloc, script = key
            if ( netloc == uriparts['host'] and 
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
    def fnhitched( self, *a, **kw ) :
        kwargs.update( kw )
        return function( *(args+a), **kwargs )
    return fnhitched.__get__( obj, cls )

def colorize( string, color, bold=False ):
    attr = []
    attr.append( color )
    attr.append('1') if bold else None
    return '\x1b[%sm%s\x1b[0m' % (';'.join(attr), string)
