# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import unittest
from   random import choice

from   pluggdapps.plugin    import PluginMeta, plugins, pluginname
from   pluggdapps.platform  import Pluggdapps

class Test_Plugin( unittest.TestCase, Singleton ):

    def test( self ):
        self.test_pluginmeta()
        super().test()

    #---- Test cases

    def test_pluginmeta( self ):
        print( "Testing plugin-meta() ..." )
        # Test plugins
        assert sorted( PluginMeta._pluginmap.keys() ) == sorted( plugins() )
        nm = choice( list( PluginMeta._pluginmap.keys() ))
        info = PluginMeta._pluginmap[nm]
        assert info['name'] == pluginname( info['cls'] )

        # Test Singleton, master_init
        p = query_plugin( None, IUnitTest, 'unittest_plugin' )
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
        print( "Testing singleton and master_init ..." )
        p = query_plugin( None, IUnitTest, 'unittest_plugin1' )
        assert p != self
        assert p.__init__.__func__.__name__ == 'masterinit'
        assert p.__init__._original.marker == 'UnitTest_Plugin1'


