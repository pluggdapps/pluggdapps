# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import logging

from   pluggdapps.plugin        import Plugin, implements, query_plugin, \
                                       ISettings
from   pluggdapps.interfaces    import ICommand

log = logging.getLogger( __name__ )

class Serve( Plugin ):
    implements( ICommand )

    description = "Start http server."
    usage = "usage: pa [options] serve [serve_options]"

    def __init__( self, platform, argv=[] ):
        self.platform = platform

    def argparse( self, argv ):
        pass

    def run( self, options=None, args=[] ):
        from pluggdapps import ROOTAPP
        platform = query_plugin( ROOTAPP, ISettings, 'platform' )
        platform.serve()
        platform.shutdown()
