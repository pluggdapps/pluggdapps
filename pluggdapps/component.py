# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import sys, types
from   utils        import whichmodule

# TODO :
#   1. How to check for multiple plugins by name name defined for same
#      Interface.

__all__ = [ 
    # API functions
    'queryPlugin', 'queryPlugins', 'implements',
    # Classes
    'Interface', 'Plugin', 'Attribute'
]

def _reflect_interface( cls, name, bases, d ):
    """`cls` is class deriving from Interface baseclass and provides 
    specification for interface `name`.
    """
    clsmod = whichmodule( cls )
    info = {
        'cls'  : cls,
        'file' : clsmod.__file__ if clsmod else '',
        'config' : {},      # Configuration dictionary for interface
        'attributes' : {},  # Map of attribute names and Attribute() object
        'methods' : {},     # Map of method names and method object
    }

    # Collect attributes and methods specified by `interface` class.
    for k in dir(cls) :
        if k.startswith('__') : continue
        v = getattr(cls, k)
        if isinstance(v, Attribute) : 
            info['attributes'][k] = v
        elif isinstance(v, types.MethodType) :
            info['methods'][k] = v

    return info


def _reflect_plugin( cls, name, bases, d ):
    """`cls` is class deriving from Plugin baseclass and implements
    interface specifications.
    """
    clsmod = whichmodule( cls.__module__ )
    info = {
        'cls'    : cls,
        'file'   : clsmod.__file__ if clsmod else '',
        'config' : {}       # Configuration dictionary for plugin
    }
    return info


class CompEnv( type ):
    """Plugin component manager."""

    # Map of interface names (which is name of the class deriving Interface
    # base class) and class object.
    _clsInterfaces = {}

    # Map of plugin names (which is name of the class deriving Plugin
    # base class) and class object.
    _clsPlugins = {}

    # Map of interface class object and list of plugin-names.
    _implementers = {}

    def __new__( cls, name, bases, d ):
        new_class = type.__new__( cls, name, bases, d )

        if name in [ 'Interface', 'Plugin' ] :
            return new_class

        if (Interface in bases) and (Plugin in bases) :
            raise Exception('Class `%s` derives both Interface and Plugin'%name)

        if Interface in bases :
            if CompEnv._clsInterfaces.has_key( name ) :
                f = CompEnv._interface[name]['file']
                raise Exception( 'Interface %r defined multiple times in %s'%f )
            CompEnv._interface_class[name] = _reflect_interface(cls, name, bases, d)
        elif Plugin in bases :
            CompEnv._clsPlugins[name] = _reflect_plugin(cls, name, bases, d)

        return new_class


class Interface( object ):
    """Base class for interface specifying classes. All interface-classes are
    metaclassed by CompEnv."""
    __metaclass__ = CompEnv


class Plugin( object ):
    """Base class for plugin classes. All plugin-classes are metaclassed by
    CompEnv."""
    __metaclass__ = CompEnv


class Attribute( object ):
    """Doc specifier for interface attributes."""
    def __init__( self, docstring ):
        self.docstring


def implements( *interfaces ):
    """Declare interfaces implemented by class. This function can be called
    only in the context of a class deriving from Plugin class."""
    frame = sys._getframe(1)
    pluginname = frame.f_code.co_name
    for i in interfaces :
        if pluginname in CompEnv._implementers[i] :
            raise Exception( 'Plugin %s is defined twice.' % pluginname )
        CompEnv._implementers.setdefault(i, []).append( pluginname )


def queryPlugins( interface, *args, **kwargs ):
    """Use this API to query for plugins using the `interface` class it
    implements. Positional and keyword arguments will be used to instantiate
    the plugin object.

    Returns a list of plugin instance implementing `interface`
    """
    return map( lambda nm : CompEnv._clsPlugins[nm]( *args, **kwargs )
                CompEnv._implementers.get(interface, []) )


def queryPlugin( interface, name, *args, **kwargs ):
    """Same as queryPlugins, but returns a single plugin instance as opposed
    an entire list. Positional and keyword arguments will be used to 
    instantiate the plugin object.
    """
    if name in CompEnv._implementers.get( interface, [] ) :
        return CompEnv._clsPlugins[name]( *args, **kwargs )
    else :
        return None
