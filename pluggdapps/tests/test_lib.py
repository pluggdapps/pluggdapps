# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import unittest, sys, time
import datetime as dt
from   random   import choice
import pkg_resources as pkg

from   pluggdapps.utils.lib import *

class UnitTest_Util( unittest.TestCase ):

    def test_sourcepath( self ):
        assert sourcepath( self ) == __file__

    def test_parsecsv( self ):
        assert parsecsv('a,b,c') == ['a','b','c']
        assert parsecsv(' a,,b,c') == ['a','b','c']
        assert parsecsv(',a,b,c,') == ['a','b','c']
        assert parsecsv(',,') == []
        assert parsecsv('') == []

    def test_parsecsvlines( self ):
        assert parsecsvlines('a,\nb\nc') == ['a','b','c']
        assert parsecsvlines(' a,\n,b,c\n') == ['a','b','c']
        assert parsecsvlines('\n,a,b,c,\n') == ['a','b','c']
        assert parsecsvlines(',\n,') == []
        assert parsecsvlines('\n') == []

    def test_classof( self ):
        assert classof( Context ) == Context
        assert classof( Context() ) == Context

    def test_subclassof( self ):
        class Base : pass
        class Derived( Base ) : pass
        d = Derived()
        assert subclassof( d, [Base] ) == Base
        assert subclassof( d, [Base, unittest.TestCase] ) == Base
        assert subclassof( d, [unittest.TestCase, Context] ) == None
        assert subclassof( d, [] ) == None

    def test_asbool( self ):
        assert asbool( 'true' ) == True
        assert asbool( 'false' ) == False
        assert asbool( 'True' ) == True
        assert asbool( 'False' ) == False
        assert asbool( True ) == True
        assert asbool( False ) == False

    def test_asint( self ):
        assert asint( '10' ) == 10
        assert asint( '10.1' ) == None
        assert asint( '10.1', True ) == True

    def test_asfloat( self ):
        assert asfloat( '10' ) == 10.0
        assert asfloat( 'hello' ) == None
        assert asfloat( 'hello', 10 ) == 10

    def test_timedelta_to_seconds( self ):
        t1 = dt.datetime.utcnow()
        time.sleep(2)
        t2 = dt.datetime.utcnow()
        assert int(timedelta_to_seconds(t2-t1)) == 2

    def test_call_entrypoint( self ):
        dist = pkg.WorkingSet().by_key['pluggdapps']
        info = call_entrypoint( dist, 'pluggdapps', 'package' )
        assert info == {}

    def test_docstr( self ):
        assert docstr(docstr) == "Return the doc-string for the object."
