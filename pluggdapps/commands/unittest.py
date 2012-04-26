# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from   optparse              import OptionParser
import logging

from   pluggdapps.plugin     import Plugin, implements, query_plugins, \
                                    pluginname
from   pluggdapps.interfaces import ICommand, IUnitTest
from   pluggdapps.unittest   import UnitTestBase

log = logging.getLogger(__name__)

class UnitTest( Plugin ):
    implements( ICommand )

    description = "Run one or more unittest."
    usage = "usage: pa [options] unittest [test_options] <module>"

    def __init__( self, platform, argv=[] ):
        self.platform = platform
        parser = self._parse( UnitTest.usage )
        self.options, self.args = parser.parse_args( argv )

    def argparse( self, argv ):
        parser = self._parse( UnitTest.usage )
        self.options, self.args = parser.parse_args( argv )
        return self.options, self.args

    def run( self, options=None, args=[] ):
        from pluggdapps import ROOTAPP
        for case in query_plugins( ROOTAPP, IUnitTest ) :
            if case.__class__ == UnitTestBase :
                continue
            if self.args :
                if self.args[0] == pluginname(case) :
                    self._run_testcase( case )
                    break;
            else :
                self._run_testcase( case )

    def _run_testcase( self, case ):
        log.info( "---- %s ----", pluginname(case) )
        case.setup( self.platform )
        case.test()
        case.teardown()

    def _parse( self, usage ):
        return self._options( OptionParser( usage=usage ))

    def _options( self, parser ):
        return parser
