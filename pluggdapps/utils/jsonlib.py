# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Convert objects from JSON format to python. And vice-versa."""

# TODO :
#   * Unit-test
#   * There are fast libraries available to do JSON encoding and decoding.

import json

__all__ = [ 'json_encode', 'json_decode' ]

def json_encode( value, encoding=None ):
    """JSON-encodes the given Python object. If `encoding` is supplied, then
    the resulting json encoded string will be converted to bytes and return
    the same, otherwise, json encodied string is returned as is."""
    # JSON permits but does not require forward slashes to be escaped.
    # This is useful when json data is emitted in a <script> tag
    # in HTML, as it prevents </script> tags from prematurely terminating
    # the javscript.  Some json libraries do this escaping by default,
    # although python's standard library does not, so we do it here.
    # http://stackoverflow.com/questions/1580647/json-why-are-forward-slashes-escaped
    s = json.dumps( value ).replace( "</", "<\\/" )
    r = s.encode( encoding ) if encoding else s
    return r

def json_decode( value, encoding=None ):
    """Convert json encoded value to Python object. If `encoding` is not
    supplied `value` is assumed to be in string, otherwise, value is expected
    in bytes and converted to string.

    Return the python object."""
    return json.loads( value.decode(encoding) if encoding else value )
