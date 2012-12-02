# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import unittest, os, os.path, posixpath, sys
from   random   import choice
from   os.path  import dirname, join

from   pluggdapps.utils.path import *
import pluggdapps.utils.path
import pluggdapps.commands

class UnitTest_Path( unittest.TestCase ):

    def test_package_path( self ):
        assert package_path(sys.modules[self.__module__]) == dirname(__file__)
        refpath = join( dirname( dirname(__file__)), 'commands', )
        assert package_path( pluggdapps.commands.unittest ) == refpath

    def test_caller_module( self ):
        assert caller_module(1) == sys.modules['pluggdapps.tests.test_path']
        assert caller_module(2) == sys.modules['unittest.case']
        assert caller_module(3) == sys.modules['unittest.case']
        assert caller_module(4) == sys.modules['unittest.case']

    def test_caller_path( self ):
        d = dirname( __file__ )
        ref1 = join(d, 'path.py')
        ref2 = '/usr/lib/python3.2/unittest/path.py'
        ref3 = '/usr/lib/python3.2/unittest/unittest.py'
        ref4 = '/usr/lib/python3.2/unittest/unittest.py'
        assert caller_path('path.py', 1) == ref1
        assert caller_path('path.py', 2) == ref2
        assert caller_path('unittest.py', 3) == ref3
        assert caller_path('unittest.py', 4) == ref4

    def test_package_name( self ):
        assert package_name(pluggdapps.commands) == 'pluggdapps.commands'
        assert package_name(pluggdapps.commands.unittest) == \
               'pluggdapps.commands'
        assert package_name(os.path) == 'posixpath'
        assert package_name(os) == 'os'

    def test_package_of( self ):
        assert package_of(pluggdapps.commands) == pluggdapps.commands
        assert package_of(pluggdapps.commands.unittest) == pluggdapps.commands
        assert package_of(os.path) == posixpath
        assert package_of(os) == os

    def test_caller_package( self ):
        assert caller_package(1) == sys.modules['pluggdapps.tests']
        assert caller_package(2) == sys.modules['unittest']
        assert caller_package(3) == sys.modules['unittest']
        assert caller_package(4) == sys.modules['unittest']


