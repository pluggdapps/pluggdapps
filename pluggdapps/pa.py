#! /usr/bin/env python

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import sys
from   optparse     import OptionParser

from   pluggdapps   import queryPlugin

def run( options, args ):
    pass

def argparse( args ):
    parser = OptionParser()
    return parser.parse_args( args )

if __name__ == '__main__' :
    from   pluggdapps.interfaces    import ICommand
    args, cmd, cmdargs = [], None, []
    for arg in sys.argv[1:] :
        if cmd == None :
            cmd = queryPlugin( ICommand, arg )
            args.append( arg ) if cmd == None else None
        else :
            cmdargs.append( arg )
    run( argparse( args ))
    cmd and cmd.run( cmd.argparse( cmdargs ))
