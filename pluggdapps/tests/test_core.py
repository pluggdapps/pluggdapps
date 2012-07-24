from pluggdapps.unittest import UnitTestBase
from pluggdapps.interfaces import IUnitTest
from random import choice

class UnitTest_Plugin( UnitTestBase ):

    def setup( self ):
        super().setup()

    def test( self ):
        self.test_whichmodule()
        super().test()

    def teardown( self ):
        super().teardown()

    #---- Test cases

    def test_whichmodule( self ):
        self.log.info("Testing whichmodule() ...")
        assert whichmodule(UnitTest_Plugin).__name__ == 'pluggdapps.plugin'
        assert whichmodule(self).__name__ == 'pluggdapps.plugin'
        assert whichmodule(whichmodule).__name__ == 'pluggdapps.plugin'

