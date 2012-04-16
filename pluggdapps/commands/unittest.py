# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from   optparse              import OptionParser

from   pluggdapps.plugin     import Plugin, implements
from   pluggdapps.interfaces import ICommand


class UnitTest( Plugin ):
    implements( ICommand )

    description = "Run one or more unittest."
    usage = "usage: pa [options] unittest [test_options] <module>"

    def __init__( self, appname, argv=[] ):
        Plugin.__init__( self, appname, argv=argv )
        parser = self._parse( UnitTest.usage )
        self.options, self.args = parser.parse_args( argv )

    def _parse( self, usage ):
        return self._options( OptionParser( usage=usage ))

    def _options( self, parser ):
        return parser

    def argparse( self, argv ):
        parser = self._parse( UnitTest.usage )
        self.options, self.args = parser.parse_args( argv )
        return self.options, self.args

    def run( self, options=None, args=[] ):
        pass
