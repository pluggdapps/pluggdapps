import unittest
from   os.path              import dirname, join
from   pprint               import pprint

import pluggdapps.config    as conf
from   pluggdapps.erlport   import Port

baseini = join( dirname( __file__ ), 'tests', 'develop.ini' )

class TestPort( Port ):

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )

    def logerror( self, formatstr, values ):
        print( formatstr, values )


port    = TestPort( descrs=(3,4) )

class TestConfig( unittest.TestCase ):

    def test_loadsettings( self ) :
        defsett = conf.defaultsettings( port )
        pprint( defsett )


if __name__ == '__main__' :
    unittest.main()
