# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

# TODO : 
#   1. Right now all packages in the environment are loaded. Instead filter
#      for pluggdapps packages and load them.

import logging
from   ConfigParser         import SafeConfigParser
from   copy                 import deepcopy

from   pluggdapps.plugin    import default_settings, applications, plugin_info

log = logging.getLogger( __name__ )

def loadsettings( inifile=None ):
    """Load root settings, application settings, and section-wise settings for
    each application. Every plugin will have its own section."""
    from pluggdapps import ROOTAPP
    rootapp = app2sec( ROOTAPP )
    appsettings = default_appsettings()
    # Override plugin defaults for each application with configuration from its
    # ini-file
    inisettings = load_inisettings( inifile ) if inifile else {}
    for appsec, sections in inisettings.items() :
        appsettings[appsec]['DEFAULT'].update( sections['DEFAULT'] )
        appcls = plugin_info( sec2app(appsec) )['cls']
        appcls.normalize_settings( appsettings[appsec]['DEFAULT'] )
        for p, sett in sections.items() :
            sett = dict( sett.items() )
            appsettings[appsec].setdefault(p, {}).update( sett )
            if is_plugin_section(p) :
                plugincls = plugin_info( sec2plugin(p) )['cls']
                plugincls.normalize_settings( appsettings[appsec][p] )
    return appsettings

def default_appsettings():
    """Compose `appsettings` from plugin's default settings."""
    from pluggdapps import ROOTAPP
    # Default settings for applications and plugins.
    rootsec = app2sec(ROOTAPP)
    appdefaults = { rootsec : {} }
    plugindefaults = {}
    appnames = applications()
    for p, sett in default_settings().items() :
        sett = dict( sett.items() )
        if p in appnames :
            appdefaults[ app2sec(p) ] = sett
        else :
            plugindefaults[ plugin2sec(p) ] = sett
    # Compose `appsettings`
    appsettings = { rootsec : { 'DEFAULT' : {} } }
    appsettings[rootsec].update( deepcopy( plugindefaults ))
    for appname in appnames :
        sett = { 'DEFAULT' : {} }
        sett['DEFAULT'].update( deepcopy( appdefaults[ app2sec(appname) ] ))
        sett.update( deepcopy( plugindefaults ))
        appsettings[ app2sec(appname) ] = sett
    return appsettings

def load_inisettings( inifile ):
    """Parse master ini configuration file and its refered ini files to
    construct a dictionary of settings for applications."""
    from pluggdapps import ROOTAPP
    log.info("Loading master configurations from %r", inifile) 
    inisettings, cp = {}, SafeConfigParser()
    cp.read( inifile )
    rootsett = { 'DEFAULT' : cp.defaults() }
    for secname in cp.sections() :
        secname = secname.strip()
        if is_app_section( secname ) :
            inisettings[secname] = loadapp( dict(cp.items( secname )))
        else :
            rootsett[secname] = deepload( secname, dict( cp.items( secname )))
    inisettings[ app2sec(ROOTAPP) ] = rootsett
    return inisettings
         

def loadapp( options ):
    """Load application settings and section-wise settings for application
    using `options` from master configuration file. `use` option if present
    will be used to load application configuration."""
    appsett = { 'DEFAULT' : options }
    cp.SafeConfigParser()
    useoption = options.get( 'use', '' )
    if useoption.startswith( 'config', '' ) :
        inifile = useoption.split(':')[1].strip()
        log.info("Loading application configuration file %r", inifile)
        cp.read( inifile )
        appsett['DEFAULT'].update( cp.defaults() )
        appsett.update( dict([ 
            ( sec, deepload( sec, dict( cp.items( sec ))) )
            for sec in cp.sections() ])
        )
    return appsett

def deepload( section, options ):
    """Check for nested configuration file under `use` option in `options`,
    if present parse their default section update this `options`."""
    cp = SafeConfigParser()
    useoption = options.get( 'use', '' )
    if useoption.startswith( 'config:' ) :
        inifile = useoption.split(':')[1].strip()
        log.info("Loading %r section's configuration from %r", inifile)
        cp.read( inifile )
        options.update( cp.defaults() )
    return options

def getsettings( appname, sec=None, plugin=None, key=None ):
    from pluggdapps import appsettings
    sec = sec or ('plugin:'+plugin if plugin else None)
    appsett = appsettings[ app2sec(appname) ]
    if sec == None :
        if key != None :
            return appsett.get( 'DEFAULT', {} ).get( key, None )
        return appsett
    elif key == None :
        return appsett.get( sec, {} )
    else :
        return appsett.get( sec, {} ).get( key, None )


def app2sec( appname ):
    return 'app:'+appname

def plugin2sec( pluginname ):
    return 'plugin:'+pluginname

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
        dict.__init__( self, *args, **kwargs )

    def __setitem__( self, name, value ):
        if not isinstance( value, (ConfigItem, dict) ) :
            raise Exception( "Type received %r not `ConfigItem` or `dict`'" )

        value = value if isinstance(value, ConfigItem) else ConfigItem(value)
        self._spec[name] = value
        val = value['default']
        return dict.__setitem__( self, name, val )

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
            str, unicode, basestring, int, bool, csv.
        Compulsory field.
    ``help``,
        Help string describing the purpose and scope of settings parameter.
    ``webconfig``,
        Boolean, specifying whether the settings parameter is configurable via
        web. Default is True.
    ``options``,
        List of optional values that can be used for configuring this 
        parameter.
    """
    fmt2str = {
        str     : 'str', unicode : 'unicode',  bool : 'bool', int   : 'int',
        'csv'   : 'csv'
    }
    def _options( self ):
        opts = self.get( 'options', '' )
        return opts() if callable(opts) else opts

    # Compulsory fields
    default = property( lambda s : s['default'] )
    formats = property( lambda s : parsecsvlines( s['formats'] ) )
    help = property( lambda s : s.get('help', '') )
    webconfig = property( lambda s : s.get('webconfig', True) )
    options = property( _options )


def settingsfor( prefix, sett ):
    """Parse `settings` keys starting with `prefix` and return a dictionary of
    corresponding options."""
    l = len(prefix)
    return dict([ (k[l:], sett[k]) for k in sett if k.startswith(prefix) ])

