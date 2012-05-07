# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

""" 
A note on how configuration becomes settings :

Dictionary of plugin configurations for each aplication. We describe here
a hierarchy of configuration sources and its priority.

  * A dictionary of settings will be parsed and populated for every loaded
    application. The settings will be organised under sections based on
    plugins, modules etc... Typical structure of settings dictionary will be,

      { 'DEFAULT'    : { <option> : <value>, ... },
        <pluginname> : { <option> : <value>, ... },
        ...
      }

    'DEFAULT' signifies the global settings for the entire application.

  * There is a root application defined by plugin :class:`RootApp`. DEFAULT
    settings for `rootapp` are in general applicable to all applications.
    Sometimes they might even be applicable to platform related
    configurations.

  * Since every application is also a plugin, their default settings, defined
    by :meth:`ISettings.default_settings` will be populated under ``DEFAULT``
    section of the settings dictionary.

  * Similarly, every loaded plugin's default settings will be popluated
    under the corresponding section of the settings dictionary.

  * Package default-settings can be overidden by configuring the one or more
    ini files. Pluggdapps platform is typically started using a master 
    configuration file which can then refer to application configuration files
    and plugin configuration files.

  * DEFAULT section configuration from master ini file overrides
    :class:`RootApp` configuration.

  * Application default-Settings can be overridden in the master ini 
    file by,

      [app:<appname>]
        key = value
        ....

  * Master configuration file, also called platform configuration file, can 
    specify separate configuration files for each loaded application like,

     [app:<appname>]
        use = config:<app-ini-file>
    
    and all sections and its configuration inside <app-ini-file> will override
    application's settings (including DEFAULT and plugin configurations).

  * plugin section names in ini files should start with `plugin:`.

  * Similar to ini files, settings can also be read from web-admin's backend
    storage. If one is available, then the sections and configuration for a 
    valid application found in the backend storage will override the
    applications settings parsed so far.

  * structure stored in web-admin's backend will be similar to this settings
    dictionary for every valid application.
"""

# TODO : Write unit-test-cases.

import configparser, collections
from   copy import deepcopy

from   pluggdapps.const import ROOTAPP
from   pluggdapps.plugin import plugin_info, query_plugin, IApplication, \
                                applications, default_settings
import pluggdapps.utils as h

def loadsettings( inifile ):
    """Load root settings, application settings, and section-wise settings for
    each application. Every plugin will have its own section."""
    appsettings = default_appsettings()
    # Override plugin defaults for each application with configuration from its
    # ini-file
    inisettings = load_inisettings( inifile )
    for appname, sections in list( inisettings.items() ) :
        appsettings[appname]['DEFAULT'].update( sections['DEFAULT'] )
        appcls = plugin_info( appname )['cls']
        appcls.normalize_settings( appsettings[appname]['DEFAULT'] )
        for p, sett in list( sections.items() ) :
            sett = dict( list( sett.items() ))
            appsettings[appname].setdefault(p, {}).update( sett )
            if is_plugin_section(p) :
                plugincls = plugin_info( sec2plugin(p) )['cls']
                plugincls.normalize_settings( appsettings[appname][p] )
    return appsettings

def default_appsettings():
    """Compose `appsettings` from plugin's default settings."""
    # Default settings for applications and plugins.
    appdefaults = { ROOTAPP : {} }
    plugindefaults = {}
    appnames = applications()
    # Fetch all the default-settings for loaded plugins using `ISettings`
    # interface
    for p, sett in default_settings().items() :
        sett = dict( sett.items() )
        if p in appnames :
            appdefaults[ p ] = sett
        else :
            plugindefaults[ plugin2sec(p) ] = sett
    # Compose `appsettings`
    appsettings = { ROOTAPP : { 'DEFAULT' : {} } }
    appsettings[ROOTAPP].update( deepcopy( plugindefaults ))
    for appname in appnames :
        sett = { 'DEFAULT' : {} }
        sett['DEFAULT'].update( deepcopy( appdefaults[ appname ] ))
        sett.update( deepcopy( plugindefaults ))
        appsettings[ appname ] = sett
    return appsettings

def load_inisettings( inifile ):
    """Parse master ini configuration file and its refered ini files to
    construct a dictionary of settings for applications."""
    inisettings, cp = {}, configparser.SafeConfigParser()
    cp.read( inifile )
    rootdefs = cp.defaults() 
    rootsett = { 'DEFAULT' : rootdefs }
    for secname in cp.sections() :
        secname = secname.strip()
        if is_app_section( secname ) :
            appname = sec2app( secname )
            inisettings[appname] = loadapp(rootdefs, dict( cp.items(secname)))
        else :
            rootsett[secname] = nestedload( dict( cp.items( secname )))
    inisettings[ ROOTAPP ] = rootsett
    for appname in list( inisettings.keys() ) :
        if appname == ROOTAPP : continue
    return inisettings
         

def loadapp( rootdefs, options ):
    """Load application settings and section-wise settings for application
    using `options` from master configuration file. `use` option if present
    will be used to load application configuration."""
    appsett = { 'DEFAULT' : deepcopy(rootdefs) }
    appsett['DEFAULT'].update( options )
    cp = configparser.SafeConfigParser()
    useoption = options.get( 'use', '' )
    if useoption.startswith( 'config:', '' ) :
        inifile = useoption.split(':')[1].strip()
        cp.read( inifile )
        appsett['DEFAULT'].update( cp.defaults() )
        appsett.update( { sec : nestedload( dict( cp.items(sec) )) }
                        for sec in cp.sections() )
    return appsett

def nestedload( options ):
    """Check for nested configuration file under `use` option in `options`,
    if present parse their default section update this `options`."""
    cp = configparser.SafeConfigParser()
    useoption = options.get( 'use', '' )
    if useoption.startswith( 'config:' ) :
        inifile = useoption.split(':')[1].strip()
        cp.read( inifile )
        options.update( cp.defaults() )
    return options

def getsettings( app, sec=None, plugin=None, key=None ):
    if isinstance( app, str ):
        app = query_plugin( app, IApplication, app )
    appsett = app.settings
    sec = sec or ('plugin:'+plugin if plugin else None)
    if sec == None :
        if key != None :
            return appsett['DEFAULT'][key]
        return appsett
    elif key == None :
        return appsett[sec]
    else :
        return appsett[sec][key]


def app2sec( appname ):
    return 'app:'+appname

def plugin2sec( pluginname ):
    return 'plugin:' + pluginname

def sec2app( secname ):
    return secname[4:]

def sec2plugin( secname ):
    return secname[7:]

def is_plugin_section( secname ):
    return secname.startswith('plugin:')

def is_app_section( secname ):
    return secname.startswith('app:')

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
        return super().__setitem( name, val )

    def specifications( self ):
        return self._spec


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

