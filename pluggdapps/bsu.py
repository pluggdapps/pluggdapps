# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

"""Byte, String, Unicode. To transform strings between bytes, str and unicode."""

__all__ = [ 
    'utf8', 'to_unicode', 'to_basestring', 'recursive_unicode', 'native_str',
]

_UTF8_TYPES = (bytes, type(None))
def utf8( value ):
    """Converts a string argument to a byte string.

    If the argument is already a byte string or None, it is returned unchanged.
    Otherwise it must be a unicode string and is encoded as utf8.
    """
    if isinstance(value, _UTF8_TYPES):
        return value
    assert isinstance(value, unicode)
    return value.encode("utf-8")

_TO_UNICODE_TYPES = (unicode, type(None))
def to_unicode( value ):
    """Converts a string argument to a unicode string.

    If the argument is already a unicode string or None, it is returned
    unchanged.  Otherwise it must be a byte string and is decoded as utf8.
    """
    if isinstance( value, _TO_UNICODE_TYPES ):
        return value
    assert isinstance( value, bytes )
    return value.decode("utf-8")

_BASESTRING_TYPES = (basestring, type(None))
def to_basestring(value):
    """Converts a string argument to a subclass of basestring.

    In python2, byte and unicode strings are mostly interchangeable,
    so functions that deal with a user-supplied argument in combination
    with ascii string constants can use either and should return the type
    the user supplied.  In python3, the two types are not interchangeable,
    so this method is needed to convert byte strings to unicode.
    """
    if isinstance(value, _BASESTRING_TYPES):
        return value
    assert isinstance(value, bytes)
    return value.decode("utf-8")

def recursive_unicode( obj ):
    """Walks a simple data structure, converting byte strings to unicode.
    Supports lists, tuples, and dictionaries.
    """
    if isinstance(obj, dict):
        return dict( (recursive_unicode(k), recursive_unicode(v))
                     for (k, v) in obj.iteritems() )
    elif isinstance(obj, list):
        return map( recursive_unicode, obj )
    elif isinstance(obj, tuple):
        return tuple( map( recursive_unicode, obj ))
    elif isinstance( obj, bytes ):
        return to_unicode(obj)
    else:
        return obj

# When dealing with the standard library across python 2 and 3 it is
# sometimes useful to have a direct conversion to the native string type
native_str = to_unicode if str is unicode else utf8


