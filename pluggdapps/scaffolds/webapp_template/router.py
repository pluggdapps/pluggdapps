# -*- coding: utf-8 -*-

from   pluggdapps.web.matchrouter import MatchRouter
from   pluggdapps.web.views       import SplashPage

class {webapp_name}Router( MatchRouter ):

    def onboot( self ):
        super().onboot()
        # Use add_view() method to add view-handlers.
        self.add_view( 'example', '/', view=SplashPage )
