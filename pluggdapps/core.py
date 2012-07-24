# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

"""Core module for pluggdapps plugin framework. It uses metaclassing to
automagically register and load plugins into query-able classes. The basic 
idea is that developers can create plugin by deriving their class from 
:class:`Plugin`. A plugin is expected to implement one or more interfaces 
using the following declaration inside their plugin class' scope.
    implements( ISettings )

The base class :class:`Plugin` itself is a plugin implementing
:class:`ISettings` interface, thus all configuration related functions are
auto-magically added to the plugin.

There is also a :class:`Singleton` base class available for plugin authors to
create singleton plugins. A singleton plugin is created only once for the
entire life time of the python environment, they are instantiated when the 
plugin is queried for the first time. Subsequent queries will fetch the 
singleton instance of the plugin.

Web-applications are plugins as well. Before any plugin can be queried, 
all application plugins must be instantiated. This is done during boot
time. Note that there can be any number of instances for a single WebApp
class.

Every other plugins must be instantiated in the context of an web-application.

Another interesting point to be noted is, all plugins are nothing but a bunch
of configuration settings gathered from sources like package-defaults,
ini-files and web-admin backend. Refer :mod:`pluggdapps.config` to learn more.

While instantiating plugins via `query_plugin()` or `query_plugins()` method,
passing a ``settings`` key-word argument will override plugin's settings
defined by ini files and web-admin.

Following data structures are preserved in memory (under the scope of
class:`PluginMeta`),

PluginMeta._interfmap =
    { <name> : <information-dictionary>,
      ...
    }

PluginMeta._pluginmap =
    { <name> : <information-dictionary>,
      ...
    }

PluginMeta._implementers =
    { <interface-class> : { <plugin-name> : <plugin-class> ,
                            ...
                          },
      ...
    }

    plugin-name is lower-cased plugin class name.

Similarly to facilitate meth:`query_plugins`, interfaces implemented by a
plugin class (and all of its base classes) are saved under the plugin class
attribute :attr:`_interfs`,

<plugin-cls>._interfs = [ <interface-class>, ... ]

"""

import sys, inspect, io
from   copy import deepcopy

from   pluggdapps.const import ROOTAPP

__all__ = [ 
    # Helper functions
    'whichmodule', 'pluginname',
    # API functions
    'implements', 
    # Classes
    'Interface', 'Attribute', 
]

core_classes = [ 'Interface', 'PluginBase', 'Singleton', ]

class PluginMeta( type ):
    """Plugin component manager."""

    _pluginmap = {}
    """A map of plugin name (which is lower-cased name of the plugin class)
    to its information dictionary."""

    _interfmap = {}
    """A map of interface name (which is name of the class deriving from
    Interface base class) to its information dictionary."""

    _implementers = {}
    """A map of interface class object to a map of plugin names and its 
    class. If a plugin sub-class derives from Singleton then query_* methods
    and functions will return the same object all the time."""

    def __new__( cls, name='', bases=(), d={} ):
        new_class = super().__new__( name, bases, d )

        if name in core_classes :
            return new_class

        new_class._interfs = []
        mro_bases = list( new_class.mro() )
        PluginMeta._sanitizecls( name, mro_bases, d )

        if Interface in mro_bases :
            # Interface's information dictionary
            PluginMeta._interfmap[name] = \
                    PluginMeta._interf( new_class, name, bases, d )

        elif PluginBase in mro_bases :
            nm = pluginname(name)
            # Plugin's information dictionary
            PluginMeta._pluginmap[nm] = \
                    PluginMeta._plugin( new_class, nm, bases, d )
            # Register deriving plugin for interfaces implemented by its base
            # classes
            for b in mro_bases :
                for i, pmap in list( PluginMeta._implementers.items() ) :
                    if pluginname(b) in pmap :
                        pmap.setdefault( nm, '-na-' )
            # Hook masterinit() for __init__ call
            init = d.get( '__init__', None )
            if init == None :
                # Because we're replacing the initializer, we need to make sure
                # that any inherited initializers are also called.
                for b in mro_bases :
                    if issubclass(b, PluginBase) and '__init__' in vars(b) :
                        init = b.__init__._original
                        break

            def masterinit( self, app, *args, **kwargs ) :
                """Plugin Init function hooked in by PluginMeta.
                Consumes ``app`` argument and initialize plugin with
                *args and **kwargs parameters. It also handles the special
                case of instantiating IWebApp plugins."""
                from pluggdapps.plugin import IWebApp, query_plugin

                # TODO : make `self.settings` into a read only copy

                # Check for instantiated singleton, if so return.
                if hasattr( self, 'settings' ): return

                self._settngx = {}
                pluginnm = pluginname(self)

                if IWebApp in type(self)._interfs : # IWebApp plugin
                    self.appname, self.app = pluginnm, self
                    self.settings = deepcopy( args[0][pluginnm] )
                    self._settngx.update( self.settings['DEFAULT'] )
                else :
                    if isinstance(app, str) :
                        self.appname = app
                        self.app = query_plugin( app, IWebApp, app )
                    else :
                        self.app = app
                        self.appname = app.appname
                    self.settings = deepcopy( self.app.settings )
                    self.globalsett = 
                    self._settngx.update( self.settings['plugin:'+pluginnm] )

                # Plugin settings
                self._settngx.update( kwargs.pop( 'settings', {} ))
                # Call the original plugin's __init__
                if init :
                    init( self, *args, **kwargs )

            masterinit._original = init
            new_class.__init__ = masterinit

        else :
            raise Exception(
                "Weird, class derives neither from Interface or PluginBase !!" )

        return new_class

    # Error messages
    err1 = 'Class `%s` derives both Interface and Plugin'
    err2 = 'Interface %r defined multiple times in %s'

    @classmethod
    def _sanitizecls( cls, name, bases, d ):
        """Perform sanitory checks on :class:`Plugin` derived classes."""
        if Interface in bases :
            if PluginBase in bases :
                raise Exception( err1 % name )
            interf = PluginMeta._interfmap.get( pluginname(name), None )
            if interf :
                raise Exception( err2 % (name, interf['file']) )

    @classmethod
    def _interf( cls, name, bases, d ):
        """`cls` is class deriving from Interface baseclass and provides 
        specification for interface `name`."""
        clsmod = whichmodule( cls )
        info = {
            'cls' : cls,
            'name' : name,
            'file' : clsmod.__file__ if clsmod else '',
            'attributes' : {},  # Map of attribute names and Attribute() object
            'methods' : {},     # Map of method names and method object
        }

        """Collect attributes and methods specified by `interface` class."""
        for k in dir(cls) :
            if k.startswith('__') : continue
            v = getattr(cls, k)
            if isinstance(v, Attribute) :
                info['attributes'][k] = v
            elif inspect.ismethod(v) :
                info['methods'][k] = v
        return info

    @classmethod
    def _plugin( cls, nm, bases, d ):
        """`cls` is class deriving from Plugin baseclass and implements
        interface specifications.
        """
        clsmod = whichmodule( cls )
        info = {
            'cls'    : cls,
            'name'   : nm,
            'file'   : clsmod.__file__ if clsmod else '',
        }
        return info


def whichmodule( attr ):
    """Try to fetch the module name in which `attr` is defined."""
    modname = getattr( attr, '__module__' )
    return sys.modules.get( modname, None ) if modname else None

def pluginname( o ):
    """Plugin names are nothing but normalized form of plugin's class name,
    where normalization is done by lower casing plugin's class name.
    
    `o` can be one of the following,
      * string
      * plugin class
      * plugin class instance
    """
    if isinstance(o, str) :
        return o.lower()
    elif inspect.isclass(o) :
        return o.__name__.lower()
    else :
        return o.__class__.__name__.lower()
    return name


class PluginBase( object, metaclass=PluginMeta ):
    """Base class for plugin classes. All plugin-classes are metaclassed by
    PluginMeta."""

    _singletons = {}
    """A map of plugin name and its singleton instance."""

    def __new__( cls, *args, **kwargs ):
        from pluggdapps.plugin import Singleton
        if issubclass( cls, Singleton ):
            name = pluginname(cls)
            singleton = PluginBase._singletons.get( name, None )
            if singleton == None :
                self = super().__new__( cls, *args, **kwargs )
                return PluginBase._singletons.setdefault( name, self )
            else :
                return singleton
        else :
            self = super().__new__( cls, *args, **kwargs )
            return self


class Interface( object, metaclass=PluginMeta ):
    """Base class for all interface specifications. All interface
    specification classes are metaclassed by PluginMeta.

    Interface is specifying a bunch of attributes and methods that provides 
    an agreement between the implementing plugins and the host that is going 
    to consume the plugin's functionality."""

    def __new__( cls, *args, **kwargs ):
        return super().__new__( cls, *args, **kwargs )
        

class Attribute( object ):
    """Doc specifier for interface attributes."""
    def __init__( self, docstring ):
        self.docstring = docstring


def implements( *interfaces ):
    """Plugin classes can use this function to declare interfaces that are 
    implemented by them. This function can be called only in the context 
    of a class deriving from :class:`Plugin`."""
    frame = sys._getframe(1)
    nm = pluginname( frame.f_code.co_name )
    for i in interfaces :
        if nm in list( PluginMeta._implementers.get(i, {}).keys() ) :
            raise Exception( 
                'Plugin %r implements interface %r twice' % (nm, i) )
        PluginMeta._implementers.setdefault( i, {} ).setdefault( nm, '-na-' )


def format_interfaces() :
    """Return a list of formated 80 column output of interfaces."""
    f = io.StringIO()
    for name, info in PluginMeta._interfmap.items() :
        format_interface( name, info, f )
        f.write("\n")
    return f.getvalue()

def format_interface( name, info, f ):
    from  pprint import pprint
    print( name, info['file'], file=f )
    print( '  attributes :' )
    pprint( info['attributes'], stream=f, indent=2 )
    print( '  methods :' )
    pprint( info['methods'], stream=f, indent=2 )

def format_plugins() :
    """Return a list of formated 80 column output of plugins."""
    f = io.StringIO()
    for name, info in PluginMeta._pluginmap.items() :
        format_plugin( name, info, f )
        f.write("\n")
    return f.getvalue()


def format_plugin( name, info, f ):
    print( name, info['file'], file=f )

def format_implementers():
    """Return a list of formated 80 column output of plugin implementation
    dictionary."""
    f = io.StringIO()
    for i, pmap in PluginMeta._implementers.items() :
        format_implementer(i, pmap)
        f.write('\n')
    return f.getvalue()

def format_implementer(i, pmap, f):
    print( i.__class__.__name__, file=f )
    pprint( pmap, stream=f, indent=2 )

