# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.


"""Byte, String, Unicode. To transform strings between bytes, str and unicode."""

import logging

from pluggdapps.compat import binary_type, text_type, string_types

__all__ = [ 
    'tobytes', 'totext', 'utf8', 'to_unicode', 'recursive_unicode', 
    'native_str', 'ascii_native'
]

log = logging.getLogger( __name__ )

def tobytes( s, encoding='utf-8', errors='strict' ):
    """Converts a string argument to a byte string, using ``encoding``.
    If the argument is not a text type, return unchanged.
    """
    if isinstance(s, text_type):
        return s.encode(encoding, errors)
    return s

def totext( s, encoding='utf-8', errors='strict' ):
    """Decodes a binary string to text string, using ``encoding``. If the 
    argument is not binary, return unchanged."""
    if isinstance(s, binary_type):
        return s.decode(encoding, errors)
    return s # pragma: no cover

def utf8( value ):
    """Converts a string argument to a byte string, using `utf8` encoding.
    If the argument is already a byte string or None, it is returned 
    unchanged."""
    return tobytes( value, encoding="utf-8" )

def to_unicode( value ):
    """Decodes a binary string to text string, using `utf8` encoding. If the 
    argument is not binary, return unchanged."""
    return totext( value, encoding="utf-8" )

def recursive_unicode( obj ):
    """Walks a simple data structure, converting byte strings to unicode.
    Supports lists, tuples, and dictionaries."""
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

from  pluggdapps.compat import ascii_native_, native_
ascii_native = ascii_native_
native_str = native_


# Unit-test
from pluggdapps.unittest import UnitTestBase

class UnitTest_BSU( UnitTestBase ):
    
    def test( self ):
        self.test_bytes_and_text()
        self.test_utf8_and_unicode()
        self.test_recursive_unicode()
        self.test_native()

    def test_bytes_and_text( self ):
        log.info("Testing tobytes() and totext() ...")
        u = u"华语/華語 Huáyǔ; 中文"
        s = u"Hello world"
        assert totext( tobytes(u, encoding='utf-8'), encoding='utf-8' ) == u
        assert totext( tobytes(s) ) == s
        u = b"华语/華語 Huáyǔ; 中文"
        s = b"Hello world"
        assert tobytes( totext(u, encoding='utf-8'), encoding='utf-8' ) == u
        assert tobytes( totext(s) ) == s

    def test_utf8_and_unicode( self ): 
        log.info("Testing utf8() and to_unicode() ...")
        u = u"华语/華語 Huáyǔ; 中文"
        s = u"Hello world"
        assert to_unicode( utf8(u) ) == u
        assert to_unicode( utf8(s) ) == s
        u = b"华语/華語 Huáyǔ; 中文"
        s = b"Hello world"
        assert utf8( to_unicode(u) ) == u
        assert utf8( to_unicode(s) ) == s

    def test_recursive_unicode( self ):
        log.info("Testing recursive_unicode() ...")
        d1 = { b"华语/華語 Huáyǔ; 中文" : b"Hello world" }
        d2 = { b"Hello world" : b"华语/華語 Huáyǔ; 中文" }
        assert recursive_unicode(d1) == { u"华语/華語 Huáyǔ; 中文" : u"Hello world" }
        assert recursive_unicode(d2) == { u"Hello world" : u"华语/華語 Huáyǔ; 中文" }

    def test_native( self ):
        log.info("Testing native_str() and ascii_native() ...")
        u = u"华语/華語 Huáyǔ; 中文"
        assert isinstance( native_str(u, encoding='utf-8'), string_types )
        u = b"华语/華語 Huáyǔ; 中文"
        assert type( ascii_native(u) ) == str
        assert isinstance( native_str(u, encoding='utf-8'), string_types )
