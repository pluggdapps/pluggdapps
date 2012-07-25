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
   { 'pluggdapps'        : <instsett>,<-|-* |       | | |
      ...                               |   |
     ('webapp:<appname>',: <instsett>,  **--*       | | |
      type, val, conf)                  |           | | |
     ...                                |           | | |
   }                                    *           | | |
                                      *-*-----------|-* |
                                      |             |   |
                                      V             *--**
             { 'webapp:<appname>'   : <settings>,       |
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
from   copy         import deepcopy
from   pprint       import pprint

from   pluggdapps.const  import MOUNT_TYPES, MOUNT_SCRIPT
import pluggdapps.utils as h

__all__ = [ 'loadsettings', 'ConfigDict', 'settingsfor', 'defaultsettings',
            'app2sec', 'sec2app', 'plugin2sec', 'sec2plugin' ]

def loadsettings( inifile ):
    """Load `inifile` and instance-wise ini files (for each web-app) and
    return them as dictionary of app settings."""
    from pluggdapps.plugin import plugin_info
    # Load application non-application plugin's default settings.
    appdefaults, plugindefaults = defaultsettings()
    # Override plugin defaults for each application with configuration from its
    # ini-file
    settings = with_inisettings( inifile, appdefaults, plugindefaults )

    # Normalize special sections
    for instkey, instsett in settings.items() :
        if not isinstance( instkey, tuple ) :
            settings[instkey] = normalize_defaults( instsett )
            continue
        for key, sett in instsett.items() :
            instsett[ key ] = normalize_defaults( sett )

    settings['pluggdapps'] = normalize_pluggdapps( settings['pluggdapps'] )
    for instkey, instsett in settings.items() :
        if not isinstance( instkey, tuple ) :
            continue
        appname,t,v,c = instkey
        for key, values in instsett.items() :
            if is_app_section(key) :    # Normalize application settings
                cls = plugin_info( sec2app(key) )['cls']
            else :                      # Normalize plugin settings
                cls = plugin_info( sec2plugin(key) )['cls']

            for b in reversed( cls.mro() ) :
                if hasattr(b, 'normalize_settings') :
                    values = b.normalize_settings( values )
            instsett[ key ] = values
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

def DEFAULT():
    """Global default settings that can be overriden by base configuration
    file's 'DEFAULT' section."""
    sett = ConfigDict()
    sett.__doc__ = "Global configuration settings with system-wide scope."
    sett['debug']  = {
        'default'  : False,
        'types'    : (bool,),
        'help'     : "Boot and run pluggdapps system in debug mode.",
        'webconfig': False,
    }
    return sett


def pluggdapps_defaultsett():
    """Default settings for pluggdapps section in ini file."""
    sett = ConfigDict()
    return sett

def normalize_defaults( sett ):
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
    from pluggdapps.plugin import default_settings, applications
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
    from pluggdapps.plugin import pluginnames, applications
    cp = configparser.SafeConfigParser()
    cp.read( inifile )
    appnames = appdefaults.keys()
    # Compute default settings for each application instance.
    instdef = {}
    instconfig = {}
    webmounts = cp.items('webmounts') if cp.has_section('webmounts') else []
    for (name, val) in webmounts :
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
    for appsec, sett in list( appdefaults.items() ) :
        instkey = ( appsec, MOUNT_SCRIPT, "/"+sec2app(appsec), None )
        if instkey in instdef :
            raise Exception("Application instance %r already defined"%instkey)
        instdef[ instkey ] = sett

    # Initialize settings 
    defaultsett = dict( DEFAULT().items() )
    defaultsett.update( cp.defaults() )
    [ sett.update( defaultsett ) for key, sett in plugindefaults.items() ]

    settings = { 'pluggdapps' : deepcopy( defaultsett ),
                 'webmounts'  : deepcopy( defaultsett ),
               }
    settings['pluggdapps'].update( dict( pluggdapps_defaultsett().items() ))
    settings['pluggdapps'].update( dict( cp.items( 'pluggdapps' )))
    settings['webmounts'].update( dict( webmounts ))

    # Create instance-wise full settings dictionary.
    for instkey, values in list( instdef.items() ):
        appsec, t, v, config = instkey
        settings[instkey] = { appsec : deepcopy(defaultsett) }
        settings[instkey][appsec].update( values )
        settings[instkey].update( deepcopy( plugindefaults ))
    settings.update( deepcopy( plugindefaults ))

    # Validate application sections and plugin sections in master ini file
    appnames = applications()
    pluginms = pluginnames()
    for secname in cp.sections() :
        if is_app_section(secname) and sec2app(secname) not in appnames :
            raise Exception( "%r web-app is not found" % secname )
        elif is_plugin_section(secname) and sec2plugin(secname) not in pluginms:
            raise Exception( "%r plugin is not found" % secname )

    # Load web-app section configuration in master ini file into app instance
    # settings
    for instkey, instsett in settings.items() :
        if not isinstance( instkey, tuple ) : continue
        appsec, t, v, config = instkey
        if cp.has_section( appsec ) :
            instsett[instkey][appsec].update( dict( cp.items( appsec )))

    # Load plugin section configuration in master ini file into app instance
    # settings
    pluginsecs = plugindefaults.keys()
    for secname in cp.sections() :
        if not is_plugin_section( secname ) : continue
        if secname not in pluginsecs :
            raise Exception( "%r is not a valid plugin" % secname )

        settings[secname].update( dict( cp.items( secname )) )
        for instkey, values in list( settings.items() ) :
            if not isinstance( instkey, tuple ) : continue
            values[secname].update( dict( cp.items( secname )) )

    # Load application configuration from master ini file and from instance
    # configuration file.
    for instkey, instsett in settings.items() :
        if not isinstance( instkey, tuple ) : continue
        appsec, t, v, configini = instkey
        if configini :
            s = loadinstance( appsec, instsett, configini )
            settings[instkey] = s
    return settings


def loadinstance( appsec, instsett, instanceini ):
    """Load configuration settings for a web application's instance."""
    cp = configparser.SafeConfigParser()
    cp.read( instanceini )
    defaultsett = dict( cp.defaults() )
    [ sett.update( defaultsett ) for key, sett in instsett.items() ]
    for secname in cp.sections() :
        instsett[secname].update( dict( cp.items( secname )))
    return instsett


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

