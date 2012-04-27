# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import logging

from   pluggdapps.plugin      import Plugin, implements
from   pluggdapps.interfaces  import IUnitTest

log = logging.getLogger( __name__ )

class UnitTestBase( Plugin ):
    implements( IUnitTest )

    def setup( self, platform ):
        self.platform = platform

    def test( self ):
        pass

    def teardown( self ):
        pass


# modules with unittest cases

import pluggdapps.asset
import pluggdapps.path
import pluggdapps.util
