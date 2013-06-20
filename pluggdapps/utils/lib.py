# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Commonly used utility functions."""

# TODO :
#   * Improve function asbool() implementation.

import sys, os, fcntl, multiprocessing, random, io, traceback, hashlib, \
       time, imp
from   os.path  import isfile, join
from   binascii import hexlify

__all__ = [
    'sourcepath', 'parsecsv', 'parsecsvlines', 'classof', 'subclassof',
    'asbool', 'asint', 'asfloat', 'timedelta_to_seconds', 'set_close_exec', 
    'set_nonblocking', 'call_entrypoint', 'docstr', 'cpu_count', 
    'reseed_random', 'mergedict', 'multivalue_dict', 'takewhile', 
    'dropwhile', 'flatten', 'print_exc', 'eval_import', 'string_import', 
    'str2module', 'locatefile', 'hitch', 'hitch_method', 'colorize', 'strof',
    'longest_prefix', 'dictsort', 'formated_filesize', 'age', 'pynamespace',
    # Classes
    'Context', 'Bunch',
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
    lines = lines if isinstance(lines, list) else lines.splitlines() 
    return parsecsv( ', '.join( lines ))


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
    ep = distribution.get_entry_info( group, name )
    return ep.load()( *args, **kwargs ) if ep else None


def docstr( obj ):
    """Return the doc-string for the object."""
    return getattr( obj, '__doc__', '' ) or ''


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

def flatten( lst ):
    """Flatten nested list ``lst`` into a flat list."""
    l = []
    for e in lst :
        if isinstance( e, list ) : l.extend( flatten( e ))
        else : l.append( e )
    return l

def print_exc() :
    """Return a string representing exception info."""
    typ, val, tb = sys.exc_info()
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
    module ``foo.bar`` with an object ``baz`` in it, or a module ``foo`` with
    an object ``bar`` with an attribute ``baz``.
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

def locatefile( phile, lookup_directories=[] ):
    """Locate the absolute path in which file ``phile` is located."""

    if phile.startswith('/') :
        return phile if isfile(phile) else None

    # First assume that file is relative to lookup_directories
    files = list( filter( 
               isfile, [ join(d, phile) for d in lookup_directories ] ))
    if files : return files[0]

    # Otherwise, assume that it is specified in asset specification notation
    try    : return h.abspath_from_asset_spec( phile )
    except : return None

    raise Exception( 'Error locating TTL file %r' % phile )

def hitch( function, *args, **kwargs ):
    """Hitch a function with a different object and different set of
    arguments."""
    def fnhitched( *a, **kw ) :
        kwargs.update( kw )
        return function( *(args+a), **kwargs )
    return fnhitched

def hitch_method( obj, cls, function, *args, **kwargs ) :
    def fnhitched( self, *a, **kw ) :
        kwargs.update( kw )
        return function( *(args+a), **kwargs )
    return fnhitched.__get__( obj, cls )

def colorize( string, color, bold=False ):
    """ Color values
    Black       0;30     Dark Gray     1;30
    Blue        0;34     Light Blue    1;34
    Green       0;32     Light Green   1;32
    Cyan        0;36     Light Cyan    1;36
    Red         0;31     Light Red     1;31
    Purple      0;35     Light Purple  1;35
    Brown       0;33     Yellow        1;33
    Light Gray  0;37     White         1;37
    """
    attr = []
    attr.append( color )
    attr.append('1') if bold else None
    return '\x1b[%sm%s\x1b[0m' % (';'.join(attr), string)

def strof( o ):
    """``o`` can be either a string or bytes or other object convertible to
    string. In case of bytes, it will be decoded using 'utf-8'. In case of
    None, None will be returned."""
    if isinstance(o, str) : return o
    elif isinstance(o, bytes) : return o.decode('utf-8')
    elif o == None : return None
    else : return str(o)

def longest_prefix( prefix_l, s ) :
    """Among the list of strings ``prefix_l``, find the longest prefix match
    for string ``s``."""
    result = None
    for p in prefix_l :
        if s.startswith( p ) :
            result = p if (result==None) or (len(p) > len(result)) else result
    return result

def dictsort( d, case=False, by='key' ) :
    """Sort a dict and yield (key, value) pairs."""
    pos = { 'key' : 0, 'value' : 1 }[ by ]
    fn = lambda x : x[pos] if case else x[pos].lower()
    return sorted( d.items(), key=fn )

def formated_filesize( size, binary=False ):
    """Format file ``size`` to human-readable file size (i.e. 13 kB, 4.1 MB,
    102 Bytes, etc).
    """
    # TODO : Should this be such a long function ??? 
    value = float(size)
    base = binary and 1024 or 1000
    prefixes = [
        (binary and 'KiB' or 'kB'),
        (binary and 'MiB' or 'MB'),
        (binary and 'GiB' or 'GB'),
        (binary and 'TiB' or 'TB'),
        (binary and 'PiB' or 'PB'),
        (binary and 'EiB' or 'EB'),
        (binary and 'ZiB' or 'ZB'),
        (binary and 'YiB' or 'YB')
    ]
    if value == 1:
        return '1 Byte'
    elif value < base:
        return '%d Bytes' % value
    else:
        for i, prefix in enumerate(prefixes):
            unit = base ** (i + 2)
            if value < unit :
                return '%.1f %s' % ((base * value / unit), prefix)
        return '%.1f %s' % ((base * value / unit), prefix)

agescales = [("year", 3600 * 24 * 365),
             ("month", 3600 * 24 * 30),
             ("week", 3600 * 24 * 7),
             ("day", 3600 * 24),
             ("hour", 3600),
             ("minute", 60),
             ("second", 1)]


def age(then, format="%a %b %d, %Y", scale="year"):
    """convert (timestamp, tzoff) tuple into an age string. both `timestamp` and
    `tzoff` are expected to be integers."""

    plural = lambda t, c : t if c == 1 else (t + "s")
    fmt = lambda t, c : "%d %s" % (c, plural(t, c))

    now = time.time()
    if then > now :
        return 'in the future'

    threshold = dropwhile( lambda x : x[0] != scale, agescales )[0][1]
    delta = max(1, int(now - then))
    if delta > threshold :
        return time.strftime(format, time.gmtime(then))

    for t, s in agescales:
        n = delta // s
        if n >= 2 or s == 1:
            return '%s ago' % fmt(t, n)

def pynamespace(module, filterfn=None):
    """if ``module`` is string import module and collect all attributes
    defined in the module that do not start with `_`. If ``__all__`` is
    defined, only fetch attributes listed under __all__. Additionally apply
    ``filterfn`` function and return a dictionary of namespace from module."""
    module = string_import(module) if isinstance(module, str) else module
    d = { k:getattr(module,k) for k in getattr(module,'__all__',vars(module)) }
    [ d.pop(k) for k,v in d.items() if filterfn(k, v) ] if filterfn else None
    return d


class ETag( dict ):
    """A dictionary like object to transparently manage context information.
    Instead of directly accessing context object to update key,value pairs,
    one can do,::

        context.etag['userinfo'] = { 'firstname' : 'bose', ... }
      
    **Notes**

      * Passes the key,value pairs assigned or updated on this object to the
        containing ``context`` object.
      * All the key,value pairs assigned or updated to this object will be
        used to compute ETag value.
      * Optionally, programs can use :meth:`hashin` to compute resource's
        hash-digest outside the context object, but nevertheless contribute to
        ETag computation.
    """

    def __init__( self, context, *args, **kwargs ):
        """Override dict.__init__ to initalize internal data strucutres."""
        super().__init__( *args, **kwargs )
        self._c = context
        self._init()

    def __setitem__( self, key, value ):
        """Override to populate the context object with key,value."""
        self._c[ key ] = value
        return super().__setitem__( key, value )

    def update( self, *args, **kwargs ):
        """Override to populate the context object with *args and **kwargs."""
        self._c.update( *args, **kwargs )
        return super().update( *args, **kwargs )

    def setdefault( self, key, value=None ):
        """Override to populate the context object with key, value."""
        self._c.setdefault( key, value )
        return super().setdefault( key, value )

    def hashin( self, hashstring ):
        """Resource objects for which etag computation and their context
        representations are different can generate hash-digest seperately and
        update them with rest of the hash-digest through this method."""
        self._hashin += hashstring.encode('utf-8') \
                            if isinstance(hashstring, str) else hashstring

    def hashout( self, prefix='', joinwith='', sep=';' ):
        """Return the hash digest so far."""
        digest = '' # Initialize
        if self.values() or self._hashin :
            [ self._hasher.update(
                v if isinstance(v, bytes) else str(v).encode('utf-8') 
              ) for v in self.values() ]
            self._hasher.update( self._hashin ) if self._hashin else None
            digest = prefix + self._hasher.hexdigest()
        return sep.join( filter( None, [joinwith, digest ]))

    def clear( self ):
        """Clear all key,value pairs so far populated on this dictionary
        object and re-initialize the hash algorithm. Note that the same 
        key, value pairs are still preserved in the context dictionary."""
        super().clear()
        self._init()

    def _init( self ):
        self._hasher = hashlib.sha1()
        self._hashin = b''


class Context( dict ):
    """Dictionary like context object passed to resource callables and view
    callables. Use of context objects has more implications than just passing
    around data values. Resource callables, typically identified by the
    request-URLs, are responsible for fetching the necessary data for
    before representing it to clients. And view callables are responsible to
    represent the data in desired format to clients. 
    """

    _specials = ['last_modified', 'etag']
    """Context key-values having special meanings."""

    etag = {}
    """Dictionary like object when updated with a (key,value) pair, typically
    a resource data,  will be used to generate a hash-digest for its value.
    The key,value pair will also be updated on this Context dictionary."""

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.etag = ETag( self )


class Bunch( object ):
    """A generic container"""

    def __init__( self, **attrs ):
        [ setattr(self, name, value) for name, value in attrs.items() ]

    def __repr__( self ):
        name = '<%s ' % self.__class__.__name__
        name += ' '.join(['%s=%r' % (name, str(value)[:30])
                          for name, value in self.__dict__.items()
                          if not name.startswith('_')])
        return name + '>'


