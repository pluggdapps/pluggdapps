# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

# TODO :
#   * Improve function asbool() implementation.

from   __future__ import absolute_import, division, with_statement
import os, fcntl, logging
import datetime as dt

__all__ = [
    'parsecsv', 'parsecsvlines', 'subclassof', 'asbool', 'asint', 'asfloat',
    'timedelta_to_seconds', 'docstr',
    'set_close_exec', 'set_nonblocking',
    'call_entrypoint',
    'ObjectDict', 'Context',
]

log = logging.getLogger( __name__ )

#---- Generic helper functions.

def parsecsv( line ):
    """Parse a single line of comma separated values, into a list of strings"""
    vals = line.split(',') if line else []
    vals = filter( None, [v.strip(' \t') for v in vals] )
    return vals


def parsecsvlines( lines ):
    """Parse a multi-line text where each line contains comma separated values.
    """
    return parsecsv( ', '.join(lines.splitlines()) )


def subclassof( cls, supers ):
    """Check whether cls is a subclass of one of the super-classes passed in
    `supers`."""
    for sup in supers :
        if issubclass( cls, sup ) : return sup
    return None


def asbool( val, default=None ):
    """Convert a string representation of boolean value to boolean type."""
    try :
        if isinstance(val, basestring) :
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
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / float(10 ** 6)

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
    
    Return the result from the called function. Note that the entrypoint must be
    uniquely identified using
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

class ObjectDict(dict):
    """Makes a dictionary behave like an object."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

class Context( dict ):
    """Dictionary like context object passed to controller methods, which in
    turn populates it with template variables, and then made available to
    template files."""
    pass

# Unit-test
from pluggdapps.unittest import UnitTestBase

class UnitTest_Util( UnitTestBase ):

    def test( self ):
        self.test_parsecsv()

    def test_parsecsv( self ):
        log.info("Testing parsecsv() ...")

