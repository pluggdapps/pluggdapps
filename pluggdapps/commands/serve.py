# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from   pluggdapps.plugin        import Plugin, implements
from   pluggdapps.interfaces    import ICommand

class Serve( Plugin ):
    implements( ICommand )

    description = "Start http server."
    usage = "usage: pa list [options] <module>"

    def __init__( self, appname, argv=[] ):
        super(Plugin, self).__init__( appname, argv=argv )

    def argparse( self, argv ):
        pass

    def run( self, options=None, args=[] ):
        pass
