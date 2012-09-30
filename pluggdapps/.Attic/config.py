# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy


import configparser, collections
from   copy         import deepcopy
from   pprint       import pprint
from   os.path      import dirname

from   pluggdapps.const  import MOUNT_TYPES, MOUNT_SCRIPT
from   pluggdapps.plugin import IConfig, Plugin
import pluggdapps.utils as h

__all__ = [ 'loadsettings', 'settingsfor', 'defaultsettings',
            'app2sec', 'sec2app', 'plugin2sec', 'sec2plugin', 'is_app_section',
            'is_plugin_section' ]

def defaultsettings():
    """By now it is expected that all interface specs and plugin definitions
    would have been loaded by loading packages implementing them and
    pluggdapps' plugin meta-classing. This function will collect their default
    settings and return them as a tuple of two dictionaries.

        (appdefaults, plugindefaults)

    appdefaults,
        { "webapp:<appname>" : default_settings,
           ...
        }

    plugindefaults
        { "plugin:<pluginname>" : default_settings,
           ...
        }
    """
    from pluggdapps.plugin import PluginMeta, applications

    # Default settings for applications and plugins.
    appdefaults, plugindefaults = {}, {}
    appnames = applications()

    # Fetch all the default-settings for loaded plugins using `ISettings`
    # interface. Plugin inheriting from other plugins will override its base's
    # default_settings() in cls.mro() order.
    for info in PluginMeta._pluginmap.values() :
        name = info['name']
        bases = reversed( info['cls'].mro() )
        sett = {}
        [ sett.update( dict( b.default_settings().items() )) for b in bases ]
        if name in appnames :
            appdefaults[ app2sec(name) ] = sett
        else :
            plugindefaults[ plugin2sec(name) ] = sett

    # Validation check
    appnames_ = sorted( list( map( app2sec, appnames )))
    if appnames_ != sorted( list( appdefaults.keys() )) :
        raise Exception( "appnames and appdefaults do not match" )
    return appdefaults, plugindefaults



def with_inisettings( baseini, appdefaults, plugindefaults ):
    """Parse master ini configuration file `baseini` and ini files refered by
    `baseini`. Construct a dictionary of settings for all application
    instances."""
    from pluggdapps.plugin import pluginnames, applications

    # context for parsing ini files.
    _vars = { 'here' : dirname(baseini) }

    # Parse master ini file.
    cp = configparser.SafeConfigParser()
    cp.read( baseini )

    # Fetch special section [webmounts]
    if cp.has_section('webmounts') :
        webmounts = cp.items( 'webmounts', vars=_vars )
    else :
        webmounts = []

    # Make local copy of appdefaults, the local copy will be used to detect
    # applications that are left un-configured in master ini file.
    appdefaults_ = deepcopy( appdefaults )

    # Compute default settings for each application instance.
    instdef = {}
    appsecs = appdefaults.keys()

    for (name, val) in webmounts :
        appsec = app2sec( name )
        if appsec not in appsecs : continue

        # Parse mount values and validate them.
        y = [ x.strip() for x in val.split(',') ]
        if len(y) == 3 :
            (t,mountname,instconfig) = y
        elif len(y) == 2 :
            (t,mountname,instconfig) = y + [None]
        else :
            raise Exception("Invalid mount configuration %r" % val)

        if t not in MOUNT_TYPES :
            raise Exception("%r for %r is not a valid mount type" % (t, name))
        
        # Settings for application instance is instantiated here for the first
        # time.
        instkey = (appsec,t,mountname,instconfig)
        if instkey in instdef :
            raise Exception( "App instance %r already defined" % instkey )
        instdef[ instkey ] = { appsec : deepcopy( appdefaults.get( appsec )) }
        appdefaults_.pop( appsec, None )

    # Compute default settings for unconfigured application instance.
    for appsec, sett in list( appdefaults_.items() ) :
        instkey = ( appsec, MOUNT_SCRIPT, "/"+sec2app(appsec), None )
        if instkey in instdef :
            raise Exception("Application instance %r already defined"%instkey)
        instdef[ instkey ] = { appsec : deepcopy(sett) }

    # Override package [DEFAULT] settings with master ini file's [DEFAULT]
    # settings.
    defaultsett1 = dict( DEFAULT().items() ) # Global defaults
    defaultsett2 = cp.defaults() )           # [DEFAULT] overriding global def.

    # Package defaults for `pluggdapps` special section. And override them
    # with [DEFAULT] settings and then with settings from master ini file's
    # [pluggdapps] section.
    settings = { 'pluggdapps' : h.mergedict(
                                    defaultsett1, 
                                    dict( pluggdapps_defaultsett().items() ),
                                    defaultsett2
                                )}
    if cp.has_section('pluggdapps') :
        settings['pluggdapps'].update(
                    dict( cp.items( 'pluggdapps', vars=_vars )))

    # Package defaults for `webmounts` special section. And override them
    # with [DEFAULT] settings.
    settings['webmounts'] = h.mergedict( defaultsett1,
                                         dict(webmounts),
                                         defaultsett2 )

    # Override plugin's package default settings with [DEFAULT] settings.
    plugindefaults = { key : h.mergedict(defaultsett1, sett, defaultsett2)
                       for key, sett plugindefaults.items() }
    settings.update( deepcopy( plugindefaults ))

    # Create instance-wise full settings dictionary.
    for instkey, values in instdef.items() :
        appsec, t, mountname, config = instkey
        settings[instkey] = { appsec : h.mergedict( defaultsett1,
                                                    values[appsec], 
                                                    defaultsett2 ) }
        settings[instkey].update( deepcopy( plugindefaults ))

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
        # Only application settings
        appsec, t, mountname, config = instkey
        if cp.has_section( appsec ) :
            instsett[appsec].update( dict( cp.items( appsec, vars=_vars )))

    # Load plugin section configuration in master ini file into app instance
    # settings
    for secname in cp.sections() :
        if not is_plugin_section( secname ) : continue
        # Only plugin settings
        settings[secname].update( dict( cp.items( secname, vars=_vars )) )
        for instkey, instsett in settings.items() :
            if not isinstance( instkey, tuple ) : continue
            instsett[secname].update( dict( cp.items( secname, vars=_vars )) )

    # Load application configuration from master ini file and from instance
    # configuration file.
    for instkey, instsett in settings.items() :
        if not isinstance( instkey, tuple ) : continue
        appsec, t, mountname, configini = instkey
        if configini :
            s = loadinstance( appsec, instsett, configini )
            settings[instkey] = s
    return settings


def loadinstance( appsec, instsett, instanceini ):
    """Load configuration settings for a web application's instance."""
    _vars = { 'here' : dirname(instanceini) }
    cp = configparser.SafeConfigParser()
    cp.read( instanceini )
    defaultsett = dict( cp.defaults() )
    [ sett.update( defaultsett ) for key, sett in instsett.items() ]
    for secname in cp.sections() :
        if secname not in instsett :
            raise Exception( "Not a valid section %r" % secname )
        instsett[secname].update( dict( cp.items( secname, vars=_vars )))
    return instsett


