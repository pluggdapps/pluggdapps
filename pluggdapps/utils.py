# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import sys

def whichmodule( attr ):
    """If `attr` contains __module__ attribute use the attribute to fetch the
    module object in which `attr` is defined"""
    modname = getattr( attr, '__module__' )
    return sys.modules.get( modname, None ) if modname else None

def parsecsv( line ) :
    """Parse a single line of comma separated values, into a list of strings"""
    vals = line and line.split( ',' ) or []
    vals = filter( None, [ v.strip(' \t') for v in vals ] )
    return vals

def parsecsvlines( lines ) :
    """Parse a multi-line text where each text contains comma separated values.
    """
    return parsecsv( ', '.join(lines.splitlines()) )

class ConfigDict( dict ):
    """A collection of configuration settings. When a fresh key, a.k.a 
    configuration parameter is added to this dictionary, it can be provided
    as `ConfigItem` object or as a dictionary containing key,value pairs
    supported by ConfigItem.
    """

    def __init__( self, *args, **kwargs ):
        self._spec = {}
        dict.__init__( self, *args, **kwargs )

    def __setitem__( self, name, value ):
        if name not in self and isinstance(value, ConfigItem) :
            self._spec[name] = value
            val = value['default']
        elif name not in self and isinstance(value, dict) :
            self._spec[name] = ConfigItem( value )
            val = value['default']
        else :
            val = value
        return dict.__setitem__( self, name, val )

    def specifications( self ):
        return self._spec

class ConfigItem( dict ):
    """Convenience class to encapsulate configuration value description, which
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

    Method call ``html(request=request)`` can be used to translate help text
    into html.
    """
    fmt2str = {
        str     : 'str', unicode : 'unicode',  bool : 'bool', int   : 'int',
        'csv'   : 'csv'
    }
    def _options( self ):
        opts = self.get( 'options', '' )
        return opts() if callable(opts) else opts

    def html( self ):
        return '<p> %s </p>' % self.help

    # Compulsory fields
    default = property( lambda s : s['default'] )
    formats = property( lambda s : parsecsvlines( s['formats'] ) )
    help = property( lambda s : s.get('help', '') )
    webconfig = property( lambda s : s.get('webconfig', True) )
    options = property( _options )


def call_entrypoint( dist, group, name, gc, **kwargs ) :
    """If an entrypoint is callable, use this api to both identify the entry
    point, evaluate them by loading and calling it. 
    
    Return the result from the called function. Note that the entrypoint must be
    uniquely identified using
        ``dist``, ``group`` and ``name``.
    """
    devmod = asbool( gc.get( 'devmod', False ))
    try :
        ep = dist.get_entry_info( group, name )
        return ep.load()( gc, **kwargs ) if ep else None
    except :
        if devmod : raise
    return None

_pluggdapps = {}    # Dictionary of { pkgname : (Distribution(), info) } pairs
def pluggdapps( global_conf={} ) :
    """Load and return a dictionary of package name and its distribution object
    (using setuptools). ``global_conf`` is from [DEFAULT] section of the
    composite.ini file.

    Note that only those packages which have ``package`` entrypoint defined
    under ``pluggdapps`` group will be loadded.
    """
    global _pluggdapps
    if _pluggdapps != {} : return _pluggdapps

    devmod = asbool( global_conf.get( 'devmod', False ))
    for pkgname, d in sorted( _packages.items(), key=lambda x : x[0] ) :
        info = call_entrypoint( d,  'pluggdapps', 'package', global_conf )
        _pluggdapps.setdefault( pkgname, (d, info) ) if info else None

    # Import all pluggdapps packages, so that the plugins get loaded.
    [ __import__(pkgname) for pkgname in _pluggdapps.keys() ]
    log.info( "%s pluggdapps packages loaded" % len(_pluggdapps) )
    return _pluggdapps 

def load_pluggdapp( loader, packageinfo, global_conf ) :
    """Load the pluggdapp application specified by ``packageinfo``.
    ``global_conf`` is expected to be parsed from initial .ini file that is use
    to load the pluggdapps platform (composite.ini).
    """
    devmod  = asbool( global_conf['devmod'] )
    appname = packageinfo['name']
    inifile = packageinfo['inifile']
    if devmod :
        reloader.watch_file( inifile.lstrip('config:') )
    try :
        if inifile :
            app = loadapp( inifile, global_conf=global_conf )
        else :
            app = loader.get_app( appname, global_conf=global_conf )
    except :
        if devmod : raise
        app = None
    log.info( '%s:%s' % (appname, inifile) )
    return app

_plugins    = {}       # { interfaceClass: {plugin-name: instance, ... }, ... }
_components = []
def buildplugins( gc, force=False ) :
    """build a dictionary of plugins based on the interface specs and
    plugin-name. Cache them for lookup.
    """
    global _plugins, _components
    if _plugins and (force == False) : return _plugins

    member = lambda x, l : any([ type(x) == type(y) for y in l ])

    _plugins = {}
    def register( interfaces, plugin ):
        for interface in interfaces :
            # Register the plugin
            z = _plugins.setdefault( interface, {} )
            l = z.setdefault( plugin.name, [] )
            l.append( plugin.component ) if not member(plugin.component, l) else None
            # Get all the bases interface definition and register for them.
            bases = list( interface.getBases() )
            bases.remove( Interface ) if Interface in bases else None
            register( bases, plugin ) if bases else None

    _components = []
    for x in gsm.registeredUtilities() :
        register( [ x.provided ], x )
        if not hasattr( x.component, 'pluginname' ) :
            raise Exception(
                '%r does not have `pluginname` attribute' % x.component
            )
        _components.append( (x.name, x.provided) )

    import pprint
    #pprint.pprint( _plugins )
    #pprint.pprint( sorted(_components, key=lambda x : x[0] ) )
    log.info(
        '%s plugins on %s interfaces' % (len(_components), len(_plugins.keys()))
    )
    return _plugins
