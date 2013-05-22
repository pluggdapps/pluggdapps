# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import sys

from   pluggdapps.plugin        import implements, Plugin, pluginname
from   pluggdapps.interfaces    import ICommand


class Info( Plugin ):
    implements( ICommand )

    description = "Platform's environment Information"
    cmd = 'info'

    def subparser( self, parser, subparsers ):
        self.subparser = subparsers.add_parser( 
                                self.cmd, description=self.description )
        self.subparser.set_defaults( handler=self.handle )

    def handle( self, args ):
        print( "Yet to be implemented" )


