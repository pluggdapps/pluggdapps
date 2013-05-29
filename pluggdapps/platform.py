# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""This module along with the :mod:`plugin` module implement the component
architechture. We expect that most of the logic written using pluggdapps will,
one way or the other, be organised as plugins implementing one or more
interface(s). This module,

* provide platform base class in whose context plugins are instantiated.
* responsible for parsing configuration parameters from various sources,
  aggregate them, make them avialable on plugin instances.
* supply methods for logging error and warning messages.

The platform is instantiated by calling the :meth:`Pluggdapps.boot` method.

**Pre-boot and boot**

Pluggdapps component system is always instantiated in the context of a
platform defined by :class:`Pluggdapps` class or by classes deriving from
`Pluggdapps`.

Platform boots in two phase, first there is a pre-boot which more or less
does every thing that is done during an actual boot and then the actual
booting. Pre-booting is designed such a way that other pluggdapps-packages can
take part in platform booting, such as loading dynamic plugins, pre-compiling
template scripts etc ...

So here is what happens duing pre-booting,

* all pluggdapps packages are loaded. But entry points are not called.
* component system is initialized by calling 
  :func:`pluggdapps.plugin.plugin_init`.
* a plain vanilla platform is instantiated using :class:`Pluggdapps`.
* configuration settings from .ini files and database backend, if available,
  is loaded.

Pre-booting comes to an end by a call to :func:`pluggdapps.callpackages`
function, which in turn is responsible for re-loading pluggdapps packages and 
calling the package entry-point. Note that package re-loading is handle in the
context of a plain vanilla platform instantiated during pre-boot phase.

During the actual boot phase, everything that was done in pre-booting phase
is repeated. But the entire blue-print of interfaces and plugins from all the
installed packages will be remembered in the context of, probably a more
sophisticated :class:`Webapps`, platform class. The choice of platform class
depends on how the user started pluggdapps.

Configuration:
--------------

Like mentioned before, platform classes are responsible for handling
configuration.

**default configuration,**

All plugins deriving from :class:`pluggdapps.plugin.Plugin` class, which is
how plugins are authored, will automatically implement 
ISettings interface. And configurable plugins must override `ISettings`
interface methods. Refer to :class:`pluggdapps.plugin.ISettings` interface to
learn more about their interface methods. When platform is booted,
default_settings from loaded plugins will be gathered and remembered.

**ini file,**

Platform is typically booted by supplying an ini-file regarded as master
configuration file. Settings in this master configuration file will override
package default settings for plugins and other `special sections`.
Configuration sections not prefixed with ``plugin:`` is considered as special
section which are explained further below.

Master configuration file can refer to other configuration file.
  
An example master configuration file,

.. code-block:: ini
    :linenos:

    [DEFAULT]
    <option> = <value>
    ... = ...

    [pluggdapps]
    <option> = <value>
    ... = ...

    [plugin:<pkgname>.<pluginname>]
    <option> = <value>
    ... = ...

    [...]

Special sections:
-----------------

**[DEFAULT]** special section. Settings from this section is applicable to all
configuration sections including plugins and referred configuration files.
Semantic meaning of [DEFAULT] section is same as described by ``configparser``
module from python stdlib.

**[pluggdapps]** special section. Settings from this section is applicable to
pluggdapps platform typically handled by :class:`Pluggdapps`.

**[mountloc]** special section. Specific to web-framework (explained below)
that is built on top of pluggdapps' component system. Provides 
configuration settings on how to mount web-applications on web-url. Handled
by :class:`Webapps` platform class.

To learn more about backend store for configuration settings refer to module,
:mod:`pluggdapps.config`.
  
Web-application platform:
-------------------------

Implemented by :class:`Webapps` class (which derives from base platform class
:class:`Pluggdapps`), it can host any number web-application, and/or instance
of same web-application in single python environment. Every web-application
is a plugin implementing :class:`pluggdapps.interfaces.IWebApp` interface.
Like mentioned above every plugin gets instantiated in the context of a
platform, and in this case, when plugins are instantiated by `IWebApp` plugin,
either directly or indirectly, the instantiated plugins are automatically
supplied with **.webapp** attribute which is now part of its context.

**[mountloc] section and application wise ini file,**

Web-applications can be mounted, hosted, on a netlocation and script-path
(collectively called as ``netpath``). This is configured under **[mountloc]**
special section. While mounting web-applications under [mountloc] additional 
configuration files can be referred. Example [mountloc] section,

.. code-block:: ini
    :linenos:

    [mountloc]
    pluggdapps.com/issues = <appname>, <ini-file>
    tayra.pluggdapps.com/issues = <appname>, <ini-file>
    tayra.pluggdapps.com/source = <appname>, <ini-file>

The `lhs` side is called netpath which typically contains subdomain, hostname
and scripth-path. The `rhs` side is a tuple of two elements. First is the
name of a `IWebApp` plugin and second is path to application configuration
file.

Referred configuration files are exclusive to the scope of the mounted
application, and shall not contain any special sections, except `[DEFAULT]`,
unless otherwise explicitly mentioned. When a plugin is instantiated in the
context of a web-application, configuration settings from application-ini-file
will override settings from the master-ini-file.
"""

from   configparser          import SafeConfigParser
from   os.path               import dirname, isfile, abspath
from   copy                  import deepcopy
import re

from   pluggdapps.const      import SPECIAL_SECS, URLSEP
from   pluggdapps.interfaces import IWebApp, IConfigDB
import pluggdapps.utils      as h

SPECIAL_SECTIONS = ['DEFAULT', 'pluggdapps']

def DEFAULT():
    """Global default settings that are applicable to all plugins and
    sections, and can be overriden by base configuration file's 'DEFAULT'
    section. Semantic meaning of [DEFAULT] section is same as described by
    ``configparser`` module from stdlib."""
    sett = h.ConfigDict()
    sett.__doc__ = (
        "Configuration settings under this section are global and applicable "
        "every other sections."
    )
    sett['debug']  = {
        'default'  : False,
        'types'    : (bool,),
        'help'     : "Set this to True while developing with pluggdapps. This "
                     "will enable useful logging and other features like "
                     "module reloading. Can be modified only in the .ini "
                     "file.",
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
    sett.__doc__ = "Platform settings."
    sett['configdb'] = {
        'default'   : 'pluggdapps.ConfigSqlite3DB',
        'types'     : (str,),
        'help'      : "Backend plugin to persist configurations done via "
                      "webadmin application. Can be modified only in the .ini "
                      "file.",
        'webconfig' : False,
    }
    sett['host'] = {
        'default'   : 'localhost',
        'types'     : (str,),
        'help'      : "Top level domain name of host, web server, which "
                      "receives the request. Can be modified only in the .ini "
                      "file.",
        'webconfig' : False,
    }
    sett['logging.file'] = {
        'default'   : '',
        'types'     : (str,),
        'help'      : "File name to log messages. Make sure to add `file` in "
                      "`logging.output` parameter."
    }
    sett['logging.output'] = {
        'default' : 'console',
        'types'   : (str,),
        'help'    : "Comma separated value of names to log messages. "
                    "Supported names are `console`, `file`.",
        'options' : [ 'console', 'file' ],
    }
    sett['port'] = {
        'default'   : 8080,
        'types'     : (int,),
        'help'      : "Port addres to bind the http server. This "
                      "configuration will be used when using pluggdapps' "
                      "native HTTP server. Can be modified only in the .ini "
                      "file.",
        'webconfig' : False,
    }
    sett['scheme'] = {
        'default'   : 'http',
        'types'     : (str,),
        'help'      : "HTTP Scheme to use, either `http` or `https`. This "
                      "configuration will be used when using pluggdapps' "
                      "native HTTP server. Can be modified only in the .ini "
                      "file.",
        'webconfig' : False,
    }
    return sett


def normalize_pluggdapps( sett ):
    """Normalize settings for [pluggdapps] special section."""
    sett['port'] = h.asint( sett['port'] )
    if isinstance( sett['logging.output'], str ):
        sett['logging.output'] = h.parsecsv( sett['logging.output'] )
    return sett

def mountloc_defaultsett():
    sett = h.ConfigDict()
    sett.__doc__ = "Mount application settings"
    return sett

def normalize_mountloc( sett ):
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

    configdb = None
    """:class:`pluggdapps.interfaces.IConfigDB` plugin instance."""

    def __init__( self, erlport=None ):
        self.erlport = erlport # TODO: Document this once bolted with netscale

    def _preboot( cls, baseini, *args, **kwargs ):
        """Prebooting. We need pre-booting because package() entry point can
        have option of creating dynamic plugins when it is called. The
        package() entry point for each and every package will be called only
        when callpackages() is called. Since callpackages() need a platform
        context, we first pre-boot the system and then actually boot the 
        system."""

        from pluggdapps import callpackages

        pa = Pluggdapps( *args, **kwargs )
        pa.settings = pa._loadsettings( baseini )

        # Configuration from backend store.
        storetype = pa.settings['pluggdapps']['configdb']
        configdb = pa.qp( pa, IConfigDB, storetype )
        configdb.dbinit()
        dbsett = configdb.config()
        if dbsett :
            [ pa.settings[section].update(d) for section, d in dbsett.items() ]

        pa.logsett = h.settingsfor( 'logging.', pa.settings['pluggdapps'] )
        callpackages( pa )
        return configdb


    #---- Overridable methods.

    @classmethod
    def boot( cls, baseini, *args, **kwargs ):
        """Boot the platform using master configuration file ``baseini``.  
        Return a new instance of this class object. This is the only way to
        create a platform instance.
        """
        configdb = Pluggdapps._preboot( cls, baseini, *args, **kwargs )

        pa = cls( *args, **kwargs )
        pa.inifile = baseini
        pa.settings = pa._loadsettings( baseini )
        pa.configdb = configdb

        # Configuration from backend store
        dbsett = pa.configdb.config()
        if dbsett :
            [ pa.settings[section].update(d) for section, d in dbsett.items() ]

        # Logging related settings go under `[pluggdapps]` section
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
        plugin._settngx.update( self.settings[ h.plugin2sec(plugin.caname) ])
        plugin.pa = self

        plugin.query_plugins = h.hitch_method( plugin, plugin.__class__,
                                      Pluggdapps.query_plugins, self )
        plugin.query_pluginr = h.hitch_method( plugin, plugin.__class__,
                                      Pluggdapps.query_pluginr, self )
        plugin.query_plugin  = h.hitch_method( plugin, plugin.__class__,
                                      Pluggdapps.query_plugin, self )

        plugin.qps = h.hitch_method( plugin, plugin.__class__,
                                     Pluggdapps.query_plugins, self )
        plugin.qpr = h.hitch_method( plugin, plugin.__class__,
                                     Pluggdapps.query_pluginr, self )
        plugin.qp  = h.hitch_method( plugin, plugin.__class__,
                                     Pluggdapps.query_plugin, self )

        # Plugin settings
        plugin._settngx.update( kwargs.pop( 'settings', {} ))

        return args, kwargs

    #---- Configuration APIs

    def config( self, **kwargs ):
        """Get or set configuration parameter for the platform. If no keyword
        arguments are supplied, will return platform-settings. This API is
        meant applications who wish to admister the platform configuration.

        Keyword arguments,

        ``section``,
            Section name to get or set config parameter. Optional.

        ``name``,
            Configuration name to get or set for ``section``. Optional.

        ``value``,
            If present, this method was invoked for setting configuration
            ``name`` under ``section``. Optional.
        """
        section = kwargs.get( 'section', None )
        name = kwargs.get( 'name', None )
        value = kwargs.get( 'value', None )
        if section and name and value :
            self.settings[section][name] = value
        return self.configdb.config( **kwargs )

    #---- Internal methods.

    def _loadsettings( self, inifile ):
        """Load ``inifile`` and override the default settings with inifile's
        configuration. Return them as dictionary of global settings."""

        SPECIAL_SECS = [ 'pluggdapps' ]
        defaults = self._defaultsettings()
        # Override plugin defaults with configuration from ini-file(s)
        return self._loadini( inifile, defaults )


    def _loadini( self, baseini, defaultsett ):
        """Parse master ini configuration file ``baseini`` and ini files
        refered by `baseini`. Construct a dictionary of settings for special
        sections and plugin sections."""
        from pluggdapps.plugin import pluginnames, plugin_info

        if not baseini or (not isfile(baseini)) :
            return deepcopy( defaultsett )

        # Initialize return dictionary.
        settings = {}

        # context for parsing ini files.
        _vars = { 'here' : abspath( dirname( baseini )) }

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
            s.update( dict( cp.items( 'pluggdapps', vars=_vars )))
            s.pop( 'here', None )   # TODO : how `here` gets populated ??
            settings['pluggdapps'] = normalize_pluggdapps( s )

        # Override plugin's package default settings with [DEFAULT] settings.
        for pluginsec, sett in defaultsett.items() :
            if not pluginsec.startswith( 'plugin:' ) : continue
            sett = h.mergedict( sett, settings['DEFAULT'] )
            if cp.has_section( pluginsec ) :
                sett.update( dict( cp.items( pluginsec, vars=_vars )))
                sett.pop( 'here', None )    # TODO : how `here` ??
            cls = plugin_info( h.sec2plugin( pluginsec ) )['cls']
            for b in reversed( cls.mro() ) :
                if hasattr( b, 'normalize_settings' ) :
                    sett = b.normalize_settings( sett )
            settings[ pluginsec ] = sett
        return settings

    def _defaultsettings( self ):
        """By now it is expected that all interface specs and plugin
        definitions would have been loaded by loading packages implementing
        them and pluggdapps' plugin meta-classing. This function will collect
        their default settings and return them as settings dictionary,::

          { "plugin:<pkgname>.<pluginname>" : default_settings,
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
        for name, info in PluginMeta._pluginmap.items() :
            bases = reversed( info['cls'].mro() )
            sett = deepcopy( default )
            for b in bases :
                if hasattr( b, 'default_settings' ) :
                    sett.update( dict( b.default_settings().items() ))
                    sett = b.normalize_settings( sett )
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
            :class:`pluggdapps.plugin.Interface` class or canonical form of
            interface-name.

        ``args`` and ``kwargs``,
            Positional and key-word arguments used to instantiate the plugin.

        If `settings` key-word argument is present, it will be used to
        override default plugin settings. Returns a list of plugin instance
        implementing `interface`
        """
        from pluggdapps.plugin import PluginMeta
        if isinstance(interface, str) :
            intrf = interface.lower()
            interface = PluginMeta._interfmap.get(intrf, {}).get('cls', None)
        pmap = PluginMeta._implementers.get(interface, {})
        return [ pcls( pa, *args, **kwargs ) for pcls in pmap.values() ]

    qps = query_plugins # Alias

    @staticmethod
    def query_pluginr( pa, interface, pattern, *args, **kwargs ):
        """Use this API to query for plugins using the ``interface`` class it
        implements. Positional and keyword arguments will be used to
        instantiate the plugin object.

        ``pa``,
            Platform object, whose base class is :class:`Pluggdapps`.

        ``interface``,
            :class:`pluggdapps.plugin.Interface` class or canonical form of
            interface-name.

        ``pattern``,
            Instantiate plugins who's name match this pattern. Pattern can be
            any regular-expression.

        ``args`` and ``kwargs``,
            Positional and key-word arguments used to instantiate the plugin.

        If `settings` key-word argument is present, it will be used to
        override default plugin settings. Returns a list of plugin instance
        implementing `interface`
        """
        from pluggdapps.plugin import PluginMeta
        if isinstance(interface, str) :
            intrf = interface.lower()
            interface = PluginMeta._interfmap.get(intrf, {}).get('cls', None)
        pattc = re.compile(pattern)
        pmap = PluginMeta._implementers.get(interface, {})
        return [ pcls( pa, *args, **kwargs )
                 for pcls in pmap.values() if re.match(pattc, pcls.caname) ]

    qpr = query_pluginr # Alias

    @staticmethod
    def query_plugin( pa, interface, name, *args, **kwargs ):
        """Same as queryPlugins, but returns a single plugin instance as
        opposed an entire list. `name` will be used to identify that plugin.
        Positional and keyword arguments will be used to instantiate the plugin
        object.

        ``pa``,
            Platform object, whose base class is :class:`Pluggdapps`.

        ``interface``,
            :class:`pluggdapps.plugin.Interface` class or canonical form of
            interface-name.

        ``name``,
            Plugin name in canonical format. For example, canonical name for 
            plugin class `ConfigSqlite3DB` defined under `pluggdapps` package
            will be, `pluggdapps.ConfigSqlite3DB`.

        ``args`` and ``kwargs``,
            Positional and key-word arguments used to instantiate the plugin.

        If ``settings`` key-word argument is present, it will be used to
        override default plugin settings. Return a single Plugin instance.
        """
        from pluggdapps.plugin import PluginMeta, ISettings
        if isinstance(interface, str) :
            intrf = interface.lower()
            interface = PluginMeta._interfmap.get(intrf, {}).get('cls', None)
        cls = PluginMeta._implementers.get(interface, {}).get(name.lower(), None)
        return cls( pa, *args, **kwargs ) if cls else None

    qp = query_plugin # Alias


    #---- platform logging

    def loginfo( self, formatstr, values=[] ):
        """Use this method to log informational messages. The log messages will
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

    def logdebug( self, formatstr, values=[] ):
        """Use this method to log debug messages. The log messages will
        be formated and handled based on the configuration settings from
        ``[pluggdapps]`` section.
        """
        if self.settings['DEFAULT']['debug'] != True : return

        output, erlport = self.logsett['output'], self.erlport
        formatstr = 'DEBUG: ' + formatstr
        if 'cloud' in output and erlport :
            self.erlport.logdebug( formatstr, values )
        if 'file' in output and self.logsett['file'] :
            open( self.logsett['file'], 'a' ).write( formatstr )
        if 'console' in output :
            print( h.colorize( formatstr, color='33' ))

    def logwarn( self, formatstr, values=[] ):
        """Use this method to log warning messages. The log messages will
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
            print( h.colorize( formatstr, color='32' ))

    def logerror( self, formatstr, values=[] ):
        """Use this method to log error messages. The log messages will
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
            print( h.colorize( formatstr, color='31' ))



class Webapps( Pluggdapps ):
    """Provides a web-framework based on a pluggable MVC design pattern. Can
    mount any number of web-application in the same python environment."""

    webapps = {}
    """Dictionay mapping of mount-key and :class:`pluggdapps.web.webapp.WebApp`
    instance, where mount-key is a tuple of appsec, netpath, application-ini"""

    netpaths= {}
    """Dictionay mapping of netpath, and :class:`pluggdapps.web.webapp.WebApp`
    instance."""

    appurls = {}
    """A dictionary map of webapp's instkey and its base-url. The base url 
    consists of scheme, netloc, scriptname."""

    _app_resolve_cache = {}
    """A dictionary map of (netloc, script-path) to Web-application object."""

    _monitoredfiles = []
    """Attribute used in debug mode to collect and monitor files that will be
    modified during developement."""

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )

    def findapp( self, appname=None, appsec=None ):
        appsec = appsec or (h.plugin2sec( appname ) if appname else None)
        if appsec :
            for asec, netpath, config in self.webapps.keys() :
                if appsec==asec : return self.webapps[(asec, netpath, config)]
            else :
                return None
        return None

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

        netpaths = [ instkey[1] for instkey, appsett in appsettings.items() ]
        pa.configdb.dbinit( netpaths=netpaths )

        # Mount webapp instances for subdomains and scripts.
        for instkey, appsett in appsettings.items() :
            appsec, netpath, config = instkey

            # Instantiate the IWebAPP plugin here for each `instkey`
            appname = h.sec2plugin( appsec )
            webapp = pa.qp( pa, instkey, IWebApp, appname, appsett )
            webapp.appsettings = appsett
            # Update with backend configuration.
            [ webapp.appsettings[section].update( d )
              for section, d in pa.configdb.config( netpath=netpath ).items() ]

            webapp.instkey, webapp.netpath = instkey, None
            pa.webapps[ instkey ] = webapp
            pa.netpaths[ netpath ] = webapp
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
        from pluggdapps.web.webapp import WebApp

        caname = plugin.caname
        if isinstance( plugin, WebApp ) : # Ought to be IWebApp plugin
            appsec, netpath, config = webapp
            plugin._settngx.update( args[0][ appsec ] )
            plugin.webapp = plugin
            args = args[1:]

        elif webapp :                   # Not a IWebApp plugin
            plugin._settngx.update( webapp.appsettings[ h.plugin2sec(caname) ])
            plugin.webapp = webapp

        else :                          # plugin not under a webapp
            plugin._settngx.update( self.settings[ h.plugin2sec(caname) ])
            plugin.webapp = None

        plugin.pa = self

        plugin.query_plugins = h.hitch_method( 
            plugin, plugin.__class__, Webapps.query_plugins,
            self, plugin.webapp )
        plugin.query_pluginr = h.hitch_method( 
            plugin, plugin.__class__, Webapps.query_pluginr,
            self, plugin.webapp )
        plugin.query_plugin = h.hitch_method(
            plugin, plugin.__class__, Webapps.query_plugin,
            self, plugin.webapp )

        plugin.qps = h.hitch_method( 
            plugin, plugin.__class__, Webapps.query_plugins,
            self, plugin.webapp )
        plugin.qpr = h.hitch_method( 
            plugin, plugin.__class__, Webapps.query_pluginr,
            self, plugin.webapp )
        plugin.qp  = h.hitch_method(
            plugin, plugin.__class__, Webapps.query_plugin,
            self, plugin.webapp )

        # Plugin settings
        plugin._settngx.update( kwargs.pop( 'settings', {} ))
        return args, kwargs

    #---- Configuration APIs

    def config( self, **kwargs ):
        """Get or set configuration parameter for the platform. If no keyword
        arguments are present, will return a dictionary of webapp-settings,
        where each webapp is identified by netpath as key.

        Keyword arguments,

        ``netpath``,
            Netpath, including hostname and script-path, on which
            web-application is mounted. Optional.

        ``section``,
            Section name to get or set config parameter. Optional.

        ``name``,
            Configuration name to get or set for ``section``. Optional.

        ``value``,
            If present, this method was invoked for setting configuration
            ``name`` under ``section``. Optional.
        """
        netpath = kwargs.get( 'netpath', None )
        if netpath == None :
            super().config( **kwargs )
        else :
            section = kwargs.get( 'section', None )
            name = kwargs.get( 'name', None )
            value = kwargs.get( 'value', None )
            if netpath == 'platform' :
                settings = self.settings
            else :
                settings = self.netpaths[ netpath ].appsettings
            if section and name and value :
                settings[section][name] = value
            return self.configdb.config( **kwargs )

    #---- Internal methods

    def _mountapps( self ):
        """Create application wise settings, using special section
        [mountloc], if any. Also parse referred configuration files."""
        from pluggdapps.plugin import pluginnames, webapps

        settings = self.settings

        # context for parsing ini files.
        _vars = { 'here' : abspath( dirname( self.inifile )) }

        # Fetch special section [mountloc]. And override them with [DEFAULT]
        # settings.
        cp = SafeConfigParser()
        cp.read( self.inifile )
        if cp.has_section('mountloc') :
            mountloc = cp.items( 'mountloc', vars=_vars )
        else :
            mountloc = []
        settings['mountloc'] = dict( mountloc )
        settings.pop( 'here', None ) # TODO : how `here` gets populated.

        # Parse mount configuration.
        appsecs = list( map( h.plugin2sec, webapps() ))
        mountls = []
        _skipopts = list(_vars.keys()) + list(settings['DEFAULT'].keys())
        for netpath, mounton in mountloc :
            if netpath in _skipopts : continue

            parts = [ x.strip() for x in mounton.split(',', 1) ]
            appname = parts.pop(0)
            configini = parts.pop(0) if parts else None
            appsec = h.plugin2sec( appname )

            if appsec not in appsecs :
                raise Exception("%r application not found." % appname )
            if not configini :
                raise Exception("configuration file %r not supplied"%configini)
            if not isfile( configini ) :
                raise Exception("configuration file %r not valid"%configini)

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
        _vars = { 'here' : abspath( dirname( instanceini )) }
        cp = SafeConfigParser()
        cp.read( instanceini )

        # Update appsett with [DEFAULT] section of instanceini
        defaultsett = normalize_defaults( dict( cp.defaults() ))
        appsett['DEFAULT'].update( defaultsett )
        [ sett.update( appsett['DEFAULT'] ) for key, sett in appsett.items() ]

        # Update plugin sections in appsett from instanceini
        for sec in cp.sections() :
            if not sec.startswith( 'plugin:' ) : continue
            sett = dict( cp.items( sec, vars=_vars ))
            sett.pop( 'here', None )    # TODO : how `here` gets populated ??
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
        port = self.settings['pluggdapps']['port']
        scheme = self.settings['pluggdapps']['scheme']
        appsec, netpath, config = instkey
        netloc, script = h.parse_netpath( netpath )

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
            :class:`pluggdapps.plugin.Interface` class or canonical form of
            interface-name.

        ``args`` and ``kwargs``,
            Positional and key-word arguments used to instantiate the plugin.

        If `settings` key-word argument is present, it will be used to
        override default plugin settings. Returns a list of plugin instance
        implementing `interface`
        """
        from pluggdapps.plugin import PluginMeta
        if isinstance(interface, str) :
            intrf = interface.lower()
            interface = PluginMeta._interfmap.get(intrf, {}).get('cls', None)
        pmap = PluginMeta._implementers.get(interface, {})
        return [ pcls( pa, webapp, *args, **kwargs ) for pcls in pmap.values() ]

    qps = query_plugins # Alias

    @staticmethod
    def query_pluginr( pa, webapp, interface, pattern, *args, **kwargs ):
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
            :class:`pluggdapps.plugin.Interface` class or canonical form of
            interface-name.

        ``pattern``,
            Instantiate plugins who's name match this pattern. Pattern can be
            any regular-expression.

        ``args`` and ``kwargs``,
            Positional and key-word arguments used to instantiate the plugin.

        If `settings` key-word argument is present, it will be used to
        override default plugin settings. Returns a list of plugin instance
        implementing `interface`
        """
        from pluggdapps.plugin import PluginMeta
        if isinstance(interface, str) :
            intrf = interface.lower()
            interface = PluginMeta._interfmap.get(intrf, {}).get('cls', None)
        pattc = re.compile(pattern)
        pmap = PluginMeta._implementers.get(interface, {})
        return [ pcls( pa, webapp, *args, **kwargs )
                 for pcls in pmap.values() if re.match(pattc, pcls.caname) ]

    qpr = query_pluginr # Alias

    @staticmethod
    def query_plugin( pa, webapp, interface, name, *args, **kwargs ):
        """Same as queryPlugins, but returns a single plugin instance as
        opposed an entire list. `name` will be used to identify that plugin.
        Positional and keyword arguments will be used to instantiate the plugin
        object.

        ``pa``,
            Platform object, whose base class is :class:`Pluggdapps`.

        ``webapp``,
            Web application object, plugin implementing
            :class:`pluggdapps.interfaces.IWebApp` interface. It is an
            optional argument, which must be passed ``None`` otherwise.

        ``interface``,
            :class:`pluggdapps.plugin.Interface` class or canonical form of
            interface-name.

        ``name``,
            plugin name in canonical format. For example, canonical name for 
            plugin class `ConfigSqlite3DB` defined under `pluggdapps` package
            will be, `pluggdapps.ConfigSqlite3DB`.

        ``args`` and ``kwargs``,
            Positional and key-word arguments used to instantiate the plugin.

        If ``settings`` key-word argument is present, it will be used to
        override default plugin settings. Return a single Plugin instance.
        """
        from pluggdapps.plugin import PluginMeta
        if isinstance(interface, str) :
            intrf = interface.lower()
            interface = PluginMeta._interfmap.get(intrf, {}).get('cls', None)
        cls = PluginMeta._implementers.get(interface, {}).get(name.lower(), None)
        return cls( pa, webapp, *args, **kwargs ) if cls else None

    qp = query_plugin   # Alias

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
        ``webapp``,
            :class:`IWebApp` plugin instance.
        """
        uriparts = h.parse_url( uri, host=hdrs.get('host', None) )
        for key, webapp in self._app_resolve_cache.items() :
            netloc, script = key
            uri_netloc = ( uriparts['host'][3:]
                            if uriparts['host'].startswith('www')
                            else uriparts['host'] )
            if netloc == uri_netloc :
                if script in ['/', ''] :
                    break
                elif uriparts['path'].startswith( script ) :
                    uriparts['script'] = script
                    uriparts['path'] = uriparts['path'][len(script):]
                    break
        else :
            webapp = None
        return uriparts, webapp
