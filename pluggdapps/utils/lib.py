# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Commonly used utility functions."""

# TODO :
#   * Improve function asbool() implementation.

import sys, os, fcntl, time, multiprocessing, random, io, traceback
import datetime as dt
from   binascii import hexlify

__all__ = [
    'sourcepath', 'parsecsv', 'parsecsvlines', 'classof', 'subclassof',
    'asbool', 'asint', 'asfloat', 'timedelta_to_seconds', 'set_close_exec', 
    'set_nonblocking', 'call_entrypoint', 'docstr', 'cpu_count', 
    'reseed_random', 'mergedict', 'multivalue_dict', 'takewhile', 
    'dropwhile', 'print_exc', 'eval_import', 'string_import', 'str2module',
    # Classes
    'Context',
]

ver_int = int( str(sys.version_info[0]) + str(sys.version_info[1]) )

#---- Generic helper functions.

def sourcepath( obj ):
    """Source path for module defining ``obj``."""
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
    **Gotcha** : if supers has a built-in type this function will fail.
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
    """Use stdlib's fcnt.fcnt() function to set FILE-DESCRIPTORS ``fds`` to be
    automatically closed when this program exits.
    """
    for fd in fds :
        flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)

def set_nonblocking( *fds ):
    """Use stdlib's fcnt.fcnt() function to set FILE-DESCRIPTORS ``fds`` to
    non-blocking read / write. 
    """
    for fd in fds :
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)


def call_entrypoint( distribution, group, name, *args, **kwargs ):
    """If an entrypoint is callable, use this API to both identify the entry
    point, evaluate them by loading and calling it. Return the result from the
    called function. Note that the entrypoint must be uniquely identified
    using, ``distribution``, ``group`` and ``name``. ``args`` and ``kwargs``
    will be passed on to the entypoint callable.
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

def mergedict( *args ) :
    """For a list of dictionaries in ``args`` return a new dictionary containing
    super-imposed key,value pairs from `args`"""
    d = {}
    [ d.update( arg ) for arg in args ]
    return d

def multivalue_dict( ls ):
    """List ``ls`` is a list of tuple (attr, value), there can be more than one
    tuple with the same `attr` name. Make a dictionary where the key values
    are list."""
    d = {}
    [ d.setdefault( k, [] ).append( v ) for k,v in ls ]
    return d

def takewhile( pred, lst ):
    """Iterate over `lst` until `pred` is True and return only the iterated
    elements."""
    r = []
    for e in lst :
        if pred(e) == False : break
        r.append(e)
    return r

def dropwhile( pred, lst ):
    """Iterate over `lst` until `pred` is True and return the remaining
    elements in `lst`."""
    i = 0
    for e in lst :
        if pred(e) == False : break
        i += 1
    return lst[i:]

def print_exc( typ, val, tb ) :
    """Return a string representing exception info."""
    f = io.StringIO()
    traceback.print_exception( typ, val, tb, file=f )
    s = f.getvalue()
    f.close()
    return s

def eval_import(s):
    """Import a module, or import an object from a module.

    A module name like ``foo.bar:baz()`` can be used, where
    ``foo.bar`` is the module, and ``baz()`` is an expression
    evaluated in the context of that module.  Note this is not safe on
    arbitrary strings because of the eval.
    """
    if ':' not in s:
        return simple_import(s)
    module_name, expr = s.split(':', 1)
    module = str2module( module_name )
    obj = eval( expr, module.__dict__ )
    return obj

def string_import( s ):
    """Import a module, object, or an attribute on an object.

    A string like ``foo.bar.baz`` can be a module ``foo.bar.baz`` or a
    module ``foo.bar`` with an object ``baz`` in it, or a module
    ``foo`` with an object ``bar`` with an attribute ``baz``.
    """
    parts = s.split('.')
    module = str2module( parts[0] )
    name = parts.pop(0)
    while parts :
        part = parts.pop(0)
        name += '.' + part
        try :
            module = str2module( name )
        except ImportError :
            parts.insert(0, part)
            break
    obj = module
    for part in parts :
        obj = getattr( obj, part )
    return obj

def str2module( s ):
    """Import a module from string specification `s`."""
    mod = __import__( s )
    parts = s.split('.')
    for part in parts[1:]:
        mod = getattr(mod, part)
    return mod

