# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from   pluggdapps.plugin        import Plugin, implements
from   pluggdapps.interfaces    import ICommand

class Serve( Plugin ):
    implements( ICommand )

    description = "Start http server."
    usage = "usage: pa [options] serve [serve_options]"

    def __init__( self, appname, argv=[] ):
        Plugin.__init__( self, appname, argv=argv )

    def argparse( self, argv ):
        pass

    def run( self, options=None, args=[] ):
        pass
