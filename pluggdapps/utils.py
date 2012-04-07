# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import sys

def whichmodule( attr ):
    """Try to fetch the module name in which `attr` is defined."""
    modname = getattr( attr, '__module__' )
    return sys.modules.get( modname, None ) if modname else None


def parsecsv( line ):
    """Parse a single line of comma separated values, into a list of strings"""
    vals = line and line.split( ',' ) or []
    vals = filter( None, [ v.strip(' \t') for v in vals ] )
    return vals


def parsecsvlines( lines ):
    """Parse a multi-line text where each line contains comma separated values.
    """
    return parsecsv( ', '.join(lines.splitlines()) )


def subclassof( cls, supers ):
    """Check whether cls is a subclass of one of the super-classes passed in
    `super`."""
    for sup in supers :
        if issubclass( cls, sup ) : return sup
    return None


def pluginname( o ):
    """Plugin names are nothing but normalized form of plugin's class name,
    where normalization is done by lower casing plugin's class name."""
    return (o if isinstance( clsname, basestring ) else o.__name__).lower()


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
