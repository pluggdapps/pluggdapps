# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

""" 
A note on how configuration becomes settings :

A dictionary of plugin (and module) configurations for each application
instance are parsed and loaded. We describe here a hierarchy of configuration
sources and its priority.

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
  [webmounts]                       |     | | |  [plugin:...]
  <appname> = (<type>, <value>)     |     | | |  ...
  <appname> = (<type>, <value>, mountini) | | |
  ...                                     | | |         Default Settings
                                          | | |         ----------------
  [webapp:<appname>] -------------------* **|-|---------- global_default = {
  <option> = <value>                    | | | |           }
  ...                                   | | | |          
                                        | | | |       *---webapp_configdict = {
  [webapp:...]                          | | | |       |   }
  ...                                   | | | |       |   ...
                                        | | | *       |   
  [plugin:<pluginname>] ----------------|-|-|-*-----* | *-plugin_configdict = {
  <option> = <value>                    | | |       | | | }
  ...                                   | | |       | | | ...
                                        | | |       | | |
  [plugin:...]                          | | |       | | |
  ...                                   | | |       | | |
                                        | | |       | | |
  Settings                              | | |       | | |
  --------                              | | |       | | |
   { 'DEFAULT'           : <instsett>,<-|-* |       | | |
     ('webapp:<appname>',: <instsett>,  **--*       | | |
      type, val, conf)                  |           | | |
     ...                                |           | | |
   }                                    *           | | |
                                      *-*-----------|-* |
                                      |             |   |
                                      V             *--**
             { 'DEFAULT'            : <settings>,       |
               'plugin:<pluginname> : <settings>, <-----*
               ...                                      
             }                                           
                                                         

  Settings store
  --------------

   structure of settings is exactly the same as that of above `Settings`
   except that, only overriden options are available in the key,value
   dictionary.

"""

import configparser, collections
from   copy import deepcopy

from   pluggdapps.const  import MOUNT_TYPES
from   pluggdapps.plugin import plugin_info, query_plugin, IWebApp, \
                                applications, default_settings
import pluggdapps.utils as h

__all__ = [ 'loadsettings', 'ConfigDict', 'settingsfor', 'defaultsettings',
            'app2sec', 'sec2app', 'plugin2sec', 'sec2plugin' ]

def loadsettings( inifile ):
    """Load `inifile` and instance-wise ini files (for each web-app) and
    return them as dictionary of app settings."""
    # Load application non-application plugin's default settings.
    appdefaults, plugindefaults = defaultsettings()
    # Override plugin defaults for each application with configuration from its
    # ini-file
    settings = with_inisettings( inifile, appdefaults, plugindefaults )

    # Normalize special sections
    settings['DEFAULT'] = normalize_global( settings['DEFAULT'] )
    settings['pluggdapps'] = normalize_pluggdapps( settings['pluggdapps'] )
    for instkey, sett in list( settings.items() ) :
        if instkey in ['DEFAULT', 'pluggdapps'] : 
            continue
        appname,t,v,c = instkey
        for key, values in list( sett.items() ) :
            if key == 'DEFAULT' :   # Normalize application settings
                cls = plugin_info( sec2app(appname) )['cls']
            else :                  # Normalize plugin settings
                cls = plugin_info( sec2plugin(key) )['cls']

            for b in reversed( cls.mro() ) :
                if hasattr(b, 'normalize_settings') :
                    values = b.normalize_settings( values )
            sett[ key ] = values
    return settings


class ConfigDict( dict ):
    """A collection of configuration settings. When a fresh key, a.k.a 
    configuration parameter is added to this dictionary, it can be provided
    as `ConfigItem` object or as a dictionary containing key,value pairs
    supported by ConfigItem.

    Used as return type for default_settings() method specified in 
    :class:`ISettings`
    """
    def __init__( self, *args, **kwargs ):
        self._spec = {}
        super().__init__( *args, **kwargs )

    def __setitem__( self, name, value ):
        if not isinstance( value, (ConfigItem, dict) ) :
            raise h.Error("ConfigDict value either be `ConfigItem` or `dict`'")

        value = value if isinstance(value, ConfigItem) else ConfigItem(value)
        self._spec[name] = value
        val = value['default']
        return super().__setitem__( name, val )

    def specifications( self ):
        return self._spec

    def merge( self, *settings ):
        settings = list( settings )
        settings.reverse()
        for sett in settings :
            for k in sett.keys() :
                if k in self : continue
                self[k] = sett[k]


class ConfigItem( dict ):
    """Convenience class to encapsulate config parameter description, which
    is a dictionary of following keys,

    ``default``,
        Default value for this settings a.k.a configuration parameter.
        Compulsory field.
    ``format``,
        Comma separated value of valid format. Allowed formats are,
            str, int, bool, csv.
        Compulsory field.
    ``help``,
        Help string describing the purpose and scope of settings parameter.
        Compulsory field.
    ``webconfig``,
        Boolean, specifying whether the settings parameter is configurable via
        web. Optional field. Default is True.
    ``options``,
        List of optional values that can be used for configuring this 
        parameter. Optional field.
    """
    @property
    def default( self ):
        return self['default']

    @property
    def format( self ):
        return parsecsvlines( self['format'] )

    @property
    def help( self ):
        return self.get('help', '')

    @property
    def webconfig( self ):
        return self.get('webconfig', True)

    @property
    def options( self ):
        opts = self.get( 'options', '' )
        return opts() if isinstance( opts, collections.Callable ) else opts


def settingsfor( prefix, sett ):
    """Parse `settings` keys starting with `prefix` and return a dictionary of
    corresponding options."""
    l = len(prefix)
    return { k[l:] : sett[k] for k in sett if k.startswith(prefix) }


#---- local functions

def global_defaultsett():
    """Global default settings that can be overriden by base configuration
    file's 'DEFAULT' section."""
    sett = ConfigDict()
    sett.__doc__ = "Global configuration settings with system-wide scope."
    sett['debug']  = {
        'default'  : False,
        'types'    : (bool,),
        'help'     : "Boot and run pluggdapps system in debug mode."
        'webconfig': False,
    }


def pluggdapps_defaultsett():
    """Default settings for pluggdapps section in ini file."""
    {}

def normalize_global( sett ):
    sett['debug'] = h.asbool( sett['debug'] )
    return sett

def normalize_pluggdapps( sett ):
    return sett

def defaultsettings():
    """By now all interface specs and plugins would have been loaded. Collect
    their default settings and return them as a dictionary.
        { "plugin:<pluginname>" : default_settings,
           ...
        }
    """
    # Default settings for applications and plugins.
    appdefaults, plugindefaults = {}, {}
    appnames = applications()
    # Fetch all the default-settings for loaded plugins using `ISettings`
    # interface
    for p, sett in default_settings().items() :
        if p in appnames :
            appdefaults[ app2sec(p) ] = sett
        else :
            plugindefaults[ plugin2sec(p) ] = sett
    # Validation check
    appnames_ = sorted( list( map( app2sec, appnames )))
    if appnames_ != sorted( list( appdefaults.keys() )) :
        raise Exception( "appnames and appdefaults do not match" )
    return appdefaults, plugindefaults


def with_inisettings( inifile, appdefaults, plugindefaults ):
    """Parse master ini configuration file and its refered ini files to
    construct a dictionary of settings for applications."""
    cp = configparser.SafeConfigParser()
    cp.read( inifile )
    appnames = appdefaults.keys()
    # Compute default settings for each application instance.
    instdef = {}
    instconfig = {}
    for (name, val) in cp.items('webmounts') :
        appname = app2sec( name )
        if appname not in appnames : # Validate
            raise Exception( "%r is not an application" % name )
        # Parse values
        y = [ x.strip() for x in val.split(',') ]
        if len(y) == 2 :
            (t,v,instconfig) = y + [None]
        else :
            (t,v,instconfig) = y
        if t not in MOUNT_TYPES : # Validate
            raise Exception("Type %r for %r not a valit mount type"%(t, name))
        instkey = (appname,t,v) 
        if instkey in instdef :
            raise Exception("Application instance %r already defined"%instkey)
        instdef[ instkey ] = appdefaults.pop( appname )
        instconfig[ instkey ] = instconfig
    # Compute default settings for unconfigured application instance.
    for appname, sett in list( appdefaults.items() ) :
        instkey = (appname, MOUNT_SCRIPT, "/"+appname)
        if instkey in instdef :
            raise Exception("Application instance %r already defined"%instkey)
        instdef[ instkey ] = sett

    # Parse the remaining master ini file and extract overriding configuration
    # for 
    #   global (DEFAULT), pluggdapps, webmounts, webapp and plugin
    # sections
    settings = { 'DEFAULT'    : global_defaultsett(),
                 'pluggdapps' : pluggdapps_defaultsett(),
               }
    settings['DEFAULT'].update( dict( cp.defaults() ))
    settings['pluggdapps'].update( dict( cp.items( 'pluggdapps' )))
    settings['webmounts'].update( dict( cp.items( 'webmounts' )))

    # Create instance-wise full settings dictionary.
    settings = {}
    for instkey, values in list( instdef.items() ):
        settings[instkey] = { 'DEFAULT' : values }
        settings.update( deepcopy( plugindefaults ))

    # First load plugin configuration from master ini file to each instance
    # settings.
    pluginsecs = plugindefaults.keys()
    for secname in cp.sections() :
        if is_plugin_section( secname ) :
            if secname not in pluginsecs :
                raise Exception( "%r is not a valid plugin" % secname )
            for instkey, values in list( settings.items() ) :
                values.update( secname=dict(cp.items(secname)) )

    # Load application configuration from master ini file and from instance
    # configuration file.
    for secname in cp.sections() :
        if secname in [ 'pluggdapps', 'webmounts' ] : continue

        if is_app_section( secname ) :
            for (appname,t,v,c), values in list( settings.items() ) :
                if appname == secname :
                    s = loadinstance( values, dict(cp.items(secname)), c )
                    settings[(appname,t,v,c)] = s
                    break
            else :
                raise Exception("%r is not a valid application" % secname)
    return settings


def loadinstance( s, defaults, instanceini ):
    """Load configuration settings for a web application's instance."""
    cp = configparser.SafeConfigParser()
    cp.read( instanceini )
    s['DEFAULT'].update( defaults )
    s['DEFAULT'].update( dict( cp.defaults ))
    for secname in cp.sections() :
        if not is_plugin_section(secname) :
            raise Exception("%r is not a plugin" % secname)
        if secname not in s :
            raise Exception("plugin %r is not present" % secname)
        s[secname].update( dict( cp.items( secname )))
    return s


def app2sec( appname ):
    return 'webapp:' + appname

def plugin2sec( pluginname ):
    return 'plugin:' + pluginname

def sec2app( secname ):
    return secname[7:]

def sec2plugin( secname ):
    return secname[7:]

def is_plugin_section( secname ):
    return secname.startswith('plugin:')

def is_app_section( secname ):
    return secname.startswith('webapp:')

