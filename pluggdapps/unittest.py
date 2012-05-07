# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

import logging

from   pluggdapps.plugin      import Plugin, implements
from   pluggdapps.interfaces  import IUnitTest

log = logging.getLogger( __name__ )

class UnitTestBase( Plugin ):
    implements( IUnitTest )

    def __init__( self, *args, **kwargs ):
        """This function is provided as part of unit-test case for checking
        masterinit() hook inside PluginMeta."""
        pass
    __init__.marker = 'UnitTestBase'

    def setup( self ):
        self.log = logging.getLogger( type(self).__name__ )

    def test( self ):
        pass

    def teardown( self ):
        pass


# modules with unittest cases

import pluggdapps.asset
import pluggdapps.path
import pluggdapps.util
