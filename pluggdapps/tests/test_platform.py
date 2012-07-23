from pluggdapps.unittest import UnitTestBase
from pluggdapps.interfaces import IUnitTest
from pluggdapps.plugin import plugins
from pluggdapps.core import PluginMeta, pluginname
from random import choice

class UnitTest_Plugin( UnitTestBase, Singleton ):

    def setup( self ):
        super().setup()

    def test( self ):
        self.test_pluginmeta()
        super().test()

    def teardown( self ):
        super().teardown()

    #---- Test cases

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


