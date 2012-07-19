# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import logging

from pluggdapps.const import ROOTAPP
from pluggdapps.core import implements, pluginname
from pluggdapps.plugin import Plugin, query_plugins
from pluggdapps.interfaces import ICommand, IUnitTest
from pluggdapps.unittest import UnitTestBase

log = logging.getLogger(__name__)

class UnitTest( Plugin ):
    implements( ICommand )

    description = "Run one or more unittest."

    def subparser( self, parser, subparsers ):
        name = pluginname( self )
        self.subparser = subparsers.add_parser( 
                                name, description=self.description )
        self.subparser.set_defaults( handler=self.handle )
        self._arguments( self.subparser )

    def handle( self, args ):
        for case in query_plugins( ROOTAPP, IUnitTest ) :
            if case.__class__ == UnitTestBase :
                continue
            if args.testname == '' :
                self._run_testcase( case )
            elif args.testname.lower() == pluginname(case) :
                self._run_testcase( case )
                break;

    def _arguments( self, parser ):
        parser.add_argument( 'testname', nargs='?', default='' )
        return parser

    def _run_testcase( self, case ):
        log.info( "---- %s ----", pluginname(case) )
        case.setup()
        case.test()
        case.teardown()

