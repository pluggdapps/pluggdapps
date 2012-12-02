# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

from   pluggdapps.web.matchrouter import MatchRouter
from   pluggdapps.web.views       import SplashPage

class docrootRouter( MatchRouter ):

    def onboot( self ):
        super().onboot()
        # Use add_view() method to add view-handlers.
        self.add_view( 'example', '/', view=SplashPage )
