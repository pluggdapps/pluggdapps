import unittest
from random import choice

class Test_Core( unittest.TestCase ):

    def test_whichmodule( self ):
        print( "Testing whichmodule() ..." )
        assert whichmodule(UnitTest_Plugin).__name__ == 'pluggdapps.plugin'
        assert whichmodule(self).__name__ == 'pluggdapps.plugin'
        assert whichmodule(whichmodule).__name__ == 'pluggdapps.plugin'

