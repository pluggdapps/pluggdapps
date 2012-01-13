# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import sys, types
from   utils    import getmodule

def _reflect_interface( cls, name, bases, d ):
    """`cls` is class deriving from Interface baseclass and provides 
    specification for interface `name`."""

    # Get module specifying interface
    clsmod = getmodule( cls.__module__ )
    info = {
        'cls'  : cls,
        'file' : clsmod.__file__ if clsmod else '',
        'config' : {},      # Configuration dictionary for interface
        'attributes' : {},  # Map of attribute names and Attribute() object
        'methods' : {},     # Map of method names and method object
        'plugins' : [],     # Map of plugin name and plugin-class
    }

    # Collect attributes and methods specified by 
    for k in dir(cls) :
        if k.startswith('__') : continue
        v = getattr(cls, k)
        if isinstance(v, Attribute) : 
            info['attributes'][k] = v
        elif isinstance(v, types.MethodType) :
            info['methods'][k] = v

    return info


def _reflect_plugin( cls, name, bases, d ):

    # Get module implementing the plugin
    clsmod = getmodule( cls.__module__ )
    info = {
        'cls'  : cls,
        'file' : clsmod.__file__ if clsmod else '',
    }
    return info


class CompEnv( type ):
    """Plugin component manager."""

    _interfaces = {}    # Collection of all interfaces
    _plugins = {}       # Collection of all plugins
    _implements = {}    # Map of plugins implementing interfaces

    def __new__( cls, name, bases, d ):
        new_class = type.__new__( cls, name, bases, d )

        if name in [ 'Interface', 'Plugin' ] :
            return new_class

        if (Interface in bases) and (Plugin in bases) :
            err = 'class cannot derive from both Interface and Plugin'
            raise Exception( err )

        if Interface in bases :
            if CompEnv._interfaces.has_key( name ) :
                f = CompEnv._interface[name]['file']
                err = 'Interface %r defined multiple times in %s' % f
                raise Exception( err )
            CompEnv._interfaces[name] = _reflect_interface(cls, name, bases, d)
        elif Plugin in bases :
            CompEnv._plugins[name] = _reflect_plugin(cls, name, bases, d)

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
    CompEnv._implements[ frame.f_code.co_name ] = interfaces


def queryPlugins( interface, *args, **kwargs ):
    """Use this API to query for plugins using the `interface` class it
    implements. Positional and keyword arguments will be used to instantiate
    the plugin object, provided plugin definition has a `__call__` method .

    A note on plugin instantiation. If the plugin provide a callable interface
    (i.e) there is a __call__ method available, then the plugin will be called
    with *args and **kwargs arguments and expects a new instance of the
    plugin.

    Returns a list of plugin instance.
    """
    cs = CompEnv._interfaces.get(interface, {}).get('plugins', {}).values()
    return [ c( *args, **kwargs ) for c in cs ]


def queryPlugin( interface, name, *args, **kwargs ):
    """Same as queryPlugins, but returns a single plugin instance as opposed
    an entire list.
    
    If optional key-word argument ``_cls`` is passed, first matching plugin
    class will be returned else, the first plugin instance, will be returned.
    """
    p = CompEnv._interfaces.get(interface, {}).get('plugins', {}).get(name, None)
    return p( *args, **kwargs )
