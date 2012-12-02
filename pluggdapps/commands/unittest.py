# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import unittest
from   os.path      import dirname, join

from   pluggdapps.plugin      import implements, Singleton, pluginname
from   pluggdapps.platform    import Pluggdapps
from   pluggdapps.interfaces  import ICommand

TESTDIR = join( dirname( dirname( __file__ )), 'tests' )

class CommandUnitTest( Singleton ):
    """Sub-command to run available unittests."""
    implements( ICommand )

    description = "Run one or more unittest."
    cmd = 'unittest'

    #---- ICommand methods

    def subparser( self, parser, subparsers ):
        """:meth:`pluggdapps.interfaces.ICommand.subparser` interface method."""
        self.subparser = subparsers.add_parser( 
                                self.cmd, description=self.description )
        self.subparser.set_defaults( handler=self.handle )
        self._arguments( self.subparser )

    def handle( self, args ):
        """:meth:`pluggdapps.interfaces.ICommand.handle` interface method."""
        tl = unittest.TestLoader()
        tr = unittest.TestResult()
        v = 2 if args.verbosity else 1
        runner = unittest.TextTestRunner( verbosity=v )
        if args.module == 'all' :
            suite = tl.discover( TESTDIR )
            runner.run( suite )
        elif args.module :
            suite = tl.loadTestsFromName( 'pluggdapps.tests.' + args.module )
            runner.run( suite )

    def _arguments( self, parser ):
        parser.add_argument( 'module', help='unittest module' )
        parser.add_argument( "-v", action="store_true", 
                             dest="verbosity",
                             help="Verbosity for running test cases" )
        return parser

