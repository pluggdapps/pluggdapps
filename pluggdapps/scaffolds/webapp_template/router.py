# -*- coding: utf-8 -*-

from   pluggdapps.web.matchrouter import MatchRouter
from   docroot.view               import SplashPage

class {webapp_name}Router( MatchRouter ):

    def onboot( self ):
        super().onboot()
        # Use add_view() method to add view-handlers.
        self.add_view( 'example', '/', view_callable=SplashPage )
