# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

"""Core module for pluggdapps plugin framework. It uses metaclassing to
automagically load plugins into query-able classes. The basic idea is that
developers can create plugin by deriving their class from :class:`Plugin`
base class. A plugin is expected to implement one or more interfaces using the
following declaration in the plugin class' scope.
    implements( ISettings )

The base class :class:`Plugin` itself is a plugin implementing
:class:`ISettings` interface.

There is also a :class:`Singleton` base class available for plugin authors to
create singleton plugins. A singleton plugin is created only once for the
entire life time of the python environment, when the plugin is queried for the
first time. Subsequent queries will fetch the singleton instance of the
plugin.

Before any plugins can be queried, all the application singletons must be
instantiated. This is done in the module :mod:`pluggdapps.platform`.

Every other plugins, including the platform singleton, must be instantiated in
the context of an application.

Another interesting point to be noted is, all plugins are nothing but a bunch
of configuration settings gathered from sources like package-defaults,
ini-files and web-admin backend. Learn more refer :mod:`pluggdapps.config`
module.

While instantiating plugins via `query_plugin()` or `query_plugins()` method,
passing a ``settings`` key-word argument will override plugin's settings
defined by ini files and web-admin.
"""

import sys, inspect, logging
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

class PluginMeta( type ):
    """Plugin component manager."""

    _pluginmap = {}
    """A map from plugin names (which is name of the class deriving Plugin base
    class) to its information dictionary."""

    _interfmap = {}
    """A map from interface names (which is name of the class deriving from
    Interface base class) to its information dictionary."""

    _implementers = {}
    """A map from interface class object to a map of plugin names and its 
    class. If a plugin sub-class derives from Singleton then query_* methods
    and functions will return the same object all the time."""

    core_classes = [ 'Interface', 'PluginBase', 'Singleton' ]

    # Error messages
    err1 = 'Class `%s` derives both Interface and Plugin'
    err2 = 'Interface %r defined multiple times in %s'

    def __new__( cls, name='', bases=(), d={} ):
        new_class = type.__new__( cls, name, bases, d )

        if name in core_classes :
            return new_class

        new_class._interfs = []
        PluginMeta._sanitizecls( name, bases, d )
        mro_bases = list( new_class.mro() )

        if Interface in mro_bases :
            # Interface's information dictionary
            _interfmap[name] = PluginMeta._interf( new_class, name, bases, d )

        elif PluginBase in mro_bases :
            nm = pluginname(name)
            # Plugin's information dictionary
            _pluginmap[nm] = PluginMeta._plugin( new_class, nm, bases, d )
            # Register deriving plugin for interfaces implemented by its base
            # classes
            for b in mro_bases :
                for i, pmap in list( _implementers.items() ) :
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
                """Component Init function hooked in by ComponentMeta.
                Consumes ``app`` argument and initialized the plugin with
                *args and **kwargs parameters. It also handles the special
                case of instantiating IApplication plugins."""
                from pluggdapps.plugin import IApplication

                # TODO : make `self.settings` into a read only copy

                self._settngx = {}
                pluginnm = pluginname(self)

                if IApplication in type(self)._interfs : # IApplication plugin
                    self.appname, self.app = pluginnm, self
                    self.settings = deepcopy( args[0][pluginnm] )
                    self._settngx.update( self.settings['DEFAULT'] )
                elif :
                    if isinstance(app, str) :
                        self.appname = app
                        self.app = query_plugin( app, IApplication, app )
                    else :
                        self.app = app
                        self.appname = app.appname
                    self.settings = deepcopy( self.app.settings )
                    self._settngx.update( self.settings['plugin:'+pluginnm] )

                # Plugin settings
                self._settngx.update( kwargs.pop( 'settings', {} ))
                # Call the original plugin's __init__
                if init :
                    init( self, *args, **kwargs )

            masterinit._original = init
            new_class.__init__ = masterinit
        return new_class

    @staticmethod
    def _sanitizecls( name, bases, d ):
        """Perform sanitory checks on :class:`Plugin` derived classes."""
        if Interface in bases :
            if PluginBase in bases :
                raise Exception( err1 % name )
            interf = _interfmap.get( pluginname(name), None )
            if interf :
                raise Exception( err2 % (name, interf['file']) )

    @staticmethod
    def _interf( cls, name, bases, d ):
        """`cls` is class deriving from Interface baseclass and provides 
        specification for interface `name`."""
        clsmod = whichmodule( cls )
        info = {
            'cls' : cls,
            'name' : name,
            'file' : clsmod.__file__ if clsmod else '',
            'config' : {},      # Configuration dictionary for interface
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

    @staticmethod
    def _plugin( cls, nm, bases, d ):
        """`cls` is class deriving from Plugin baseclass and implements
        interface specifications.
        """
        clsmod = whichmodule( cls )
        info = {
            'cls'    : cls,
            'name'   : nm,
            'file'   : clsmod.__file__ if clsmod else '',
            'config' : {}       # Configuration dictionary for plugin
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
        if issubclass( cls, Singleton ):
            name = pluginname(cls)
            singleton = _singletons.get( name, None )
            if singleton == None :
                self = super().__new__( cls, *args, **kwargs )
                return _singletons.setdefault( name, self )
            else :
                return singleton
        else :
            return super().__new__( cls, *args, **kwargs )


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


# Unit-test
from pluggdapps.unittest import UnitTestBase
from pluggdapps.interfaces import IUnitTest
from random import choice

class UnitTest_Plugin( UnitTestBase, Singleton ):

    def setup( self ):
        super().setup()

    def test( self ):
        self.test_whichmodule()
        self.test_pluginmeta()
        super().test()

    def teardown( self ):
        super().teardown()

    #---- Test cases

    def test_whichmodule( self ):
        self.log.info("Testing whichmodule() ...")
        assert whichmodule(UnitTest_Plugin).__name__ == 'pluggdapps.plugin'
        assert whichmodule(self).__name__ == 'pluggdapps.plugin'
        assert whichmodule(whichmodule).__name__ == 'pluggdapps.plugin'

    def test_pluginmeta( self ):
        self.log.info("Testing plugin-meta() ...")
        # Test plugins
        assert sorted( PluginMeta._pluginmap.keys() ) == sorted( plugins() )
        nm = choice( list( PluginMeta._pluginmap.keys() ))
        info = PluginMeta._pluginmap[nm]
        assert info['name'] == pluginname( info['cls'] )

        # Test Singleton, master_init
        p = query_plugin( ROOTAPP, IUnitTest, 'unittest_plugin' )
        assert p == self
        assert p.__init__.__func__.__name__ == 'masterinit'
        assert p.__init__._original.marker == 'UnitTestBase'


class UnitTest_Plugin1( UnitTestBase ):

    def __init__( self, *args, **kwargs ):
        pass
    __init__.marker = 'UnitTest_Plugin1'

    def setup( self ):
        super().setup()

    def test( self ):
        self.test_pluginmeta()
        super().test()

    def teardown( self ):
        super().teardown()

    #---- Test cases

    def test_pluginmeta( self ):
        self.log.info("Testing singleton and master_init ...")
        p = query_plugin( ROOTAPP, IUnitTest, 'unittest_plugin1' )
        assert p != self
        assert p.__init__.__func__.__name__ == 'masterinit'
        assert p.__init__._original.marker == 'UnitTest_Plugin1'

