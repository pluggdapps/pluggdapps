# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# TODO :
#   * Improve function asbool() implementation.

import sys, os, fcntl, time, multiprocessing, random
import datetime as dt
from   binascii import hexlify

__all__ = [
    'sourcepath', 'parsecsv', 'parsecsvlines', 'classof', 'subclassof',
    'asbool', 'asint', 'asfloat', 'timedelta_to_seconds', 'set_close_exec', 
    'set_nonblocking', 'call_entrypoint', 'docstr', 'cpu_count', 
    'reseed_random',
    # Classes
    'Context',
]

ver_int = int( str(sys.version_info[0]) + str(sys.version_info[1]) )

#---- Generic helper functions.

def sourcepath( obj ):
    mod = getattr( obj, '__module__', None )
    if mod :
        module = sys.modules[mod]
        return module.__file__
    return None

def parsecsv( line ):
    """Parse a single line of comma separated values, into a list of strings"""
    vals = line.split(',') if line else []
    vals = [ x for x in [v.strip(' \t') for v in vals] if x ]
    return vals

def parsecsvlines( lines ):
    """Parse a multi-line text where each line contains comma separated values.
    """
    return parsecsv( ', '.join(lines.splitlines()) )


def classof( obj ): 
    """If `obj` is class object return the same. Other wise assume that it is
    an instance object and return its class."""
    if isinstance( obj, type ) : 
        return obj
    else : 
        return getattr( obj, '__class__', None )

def subclassof( cls, supers ):
    """Check whether cls is a subclass of one of the super-classes passed in
    `supers`.
    
    Gotcha : if supers has a built-in type this function will fail.
    """
    cls = classof(cls)
    for sup in supers :
        if issubclass( cls, sup ) : return sup
    return None


def asbool( val, default=None ):
    """Convert a string representation of boolean value to boolean type."""
    try :
        if val and isinstance(val, str) :
            v = True if val.lower() == 'true' else False
        else :
            v = bool(val)
    except :
        v = default
    return v

def asint( val, default=None ):
    """Convert string representation of integer value to integer type."""
    try    : v = int( val )
    except : v = default
    return v

def asfloat( val, default=None ):
    """Convert string representation of float value to floating type."""
    try    : v = float( val )
    except : v = default
    return v


def timedelta_to_seconds( td ) :
    """Equivalent to td.total_seconds() (introduced in python 2.7)."""
    if ver_int >= 27 :
        sec = td.total_seconds()
    else :
        sec= (td.microseconds + 
                (td.seconds + td.days * 24 * 3600) * 10 ** 6) / float(10 ** 6)
    return sec


def set_close_exec( *fds ):
    for fd in fds :
        flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)

def set_nonblocking( *fds ):
    for fd in fds :
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)


def call_entrypoint( distribution, group, name, *args, **kwargs ):
    """If an entrypoint is callable, use this api to both identify the entry
    point, evaluate them by loading and calling it. 
    
    Return the result from the called function. Note that the entrypoint must
    be uniquely identified using
        ``dist``, ``group`` and ``name``.
    """
    devmod = kwargs.pop( 'devmod', False )
    try :
        ep = distribution.get_entry_info( group, name )
        return ep.load()( *args, **kwargs ) if ep else None
    except :
        if devmod : raise
    return None


def docstr( obj ):
    """Return the doc-string for the object."""
    return getattr( obj, '__doc__', '' ) or ''


class Context( dict ):
    """Dictionary like context object passed to controller methods, which in
    turn populates it with template variables, and then made available to
    template files."""
    pass

def cpu_count():
    """Returns the number of processors on this machine."""
    return multiprocessing.cpu_count()

def reseed_random():
    """If os.urandom is available, this method does the same thing as
    random.seed ! (at least as of python 2.6).  If os.urandom is not 
    available, we mix in the pid in addition to a timestamp."""
    random.seed( int( hexlify( os.urandom(16) ), 16 ))


# Unit-test
from pluggdapps.unittest import UnitTestBase
from random              import choice

class UnitTest_Util( UnitTestBase ):

    def setup( self ):
        super().setup()

    def test( self ):
        self.test_parsecsv()
        self.test_parsecsvlines()
        self.test_classof()
        self.test_subclassof()
        self.test_asbool()
        self.test_asint()
        self.test_asfloat()
        self.test_call_entrypoint()
        self.test_docstr()
        self.test_timedelta_to_seconds()
        super().test()

    def teardown( self ):
        super().teardown()

    def test_parsecsv( self ):
        self.log.info("Testing parsecsv() ...")
        assert parsecsv('a,b,c') == ['a','b','c']
        assert parsecsv(' a,,b,c') == ['a','b','c']
        assert parsecsv(',a,b,c,') == ['a','b','c']
        assert parsecsv(',,') == []
        assert parsecsv('') == []

    def test_parsecsvlines( self ):
        self.log.info("Testing parsecsvlines() ...")
        assert parsecsvlines('a,\nb\nc') == ['a','b','c']
        assert parsecsvlines(' a,\n,b,c\n') == ['a','b','c']
        assert parsecsvlines('\n,a,b,c,\n') == ['a','b','c']
        assert parsecsvlines(',\n,') == []
        assert parsecsvlines('\n') == []

    def test_classof( self ):
        self.log.info("Testing classof() ...")
        assert classof( Context ) == Context
        assert classof( Context() ) == Context

    def test_subclassof( self ):
        self.log.info("Testing subclassof() ...")
        class Base : pass
        class Derived( Base ) : pass
        d = Derived()
        assert subclassof( d, [Base] ) == Base
        assert subclassof( d, [Base, UnitTestBase] ) == Base
        assert subclassof( d, [UnitTestBase, Context] ) == None
        assert subclassof( d, [] ) == None

    def test_asbool( self ):
        self.log.info("Testing asbool() ...")
        assert asbool( 'true' ) == True
        assert asbool( 'false' ) == False
        assert asbool( 'True' ) == True
        assert asbool( 'False' ) == False
        assert asbool( True ) == True
        assert asbool( False ) == False

    def test_asint( self ):
        self.log.info("Testing asint() ...")
        assert asint( '10' ) == 10
        assert asint( '10.1' ) == None
        assert asint( '10.1', True ) == True

    def test_asfloat( self ):
        self.log.info("Testing asfloat() ...")
        assert asfloat( '10' ) == 10.0
        assert asfloat( 'hello' ) == None
        assert asfloat( 'hello', 10 ) == 10

    def test_timedelta_to_seconds( self ):
        self.log.info("Testing timedelta_to_seconds() ...")
        t1 = dt.datetime.utcnow()
        time.sleep(2)
        t2 = dt.datetime.utcnow()
        assert int(timedelta_to_seconds(t2-t1)) == 2

    def test_call_entrypoint( self ):
        import pkg_resources as pkg
        self.log.info("Testing call_entrypoint() ...")
        dist = pkg.WorkingSet().by_key['pluggdapps']
        info = call_entrypoint( dist, 'pluggdapps', 'package' )
        assert info == {}

    def test_docstr( self ):
        self.log.info("Testing docstr() ...")
        assert docstr(docstr) == "Return the doc-string for the object."
