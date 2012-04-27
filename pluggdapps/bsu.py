# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

"""Byte, String, Unicode. To transform strings between bytes, str and unicode."""

from pluggdapps.compat import binary_type, text_type, string_types

__all__ = [ 
    'tobytes', 'totext', 'utf8', 'to_unicode', 'recursive_unicode', 
    'native_str', 'ascii_native'
]

def tobytes( s, encoding='latin-1', errors='strict' ):
    """Converts a string argument to a byte string, using ``encoding``.
    If the argument is not a text type, return unchanged.
    """
    if isinstance(s, text_type):
        return s.encode(encoding, errors)
    return s

def totext( s, encoding='latin-1', errors='strict' ):
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
        self.test_tobytes()
        self.test_totext()
        self.test_utf8()
        self.test_to_unicode()
        self.test_recursive_unicode()
        self.test_ascii_native()
        self.test_native_str()

    def test_tobytes():
        log.info("Testing tobytes() ...")

    def test_totext():
        log.info("Testing tobytes() ...")

    def test_utf8():
        log.info("Testing tobytes() ...")

    def test_to_unicode():
        log.info("Testing tobytes() ...")

    def test_recursive_unicode():
        log.info("Testing tobytes() ...")

    def test_ascii_native():
        log.info("Testing tobytes() ...")

    def test_native_str():
        log.info("Testing tobytes() ...")

