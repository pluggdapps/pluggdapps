# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

"""Convert objects from JSON format to python. And vice-versa."""

# TODO :
#   1. There are fast libraries available to do JSON encoding and decoding.
#   Explore them.

import json

__all__ = [ 'json_encode', 'json_decode' ]

def json_encode( value ):
    """JSON-encodes the given Python object."""
    # JSON permits but does not require forward slashes to be escaped.
    # This is useful when json data is emitted in a <script> tag
    # in HTML, as it prevents </script> tags from prematurely terminating
    # the javscript.  Some json libraries do this escaping by default,
    # although python's standard library does not, so we do it here.
    # http://stackoverflow.com/questions/1580647/json-why-are-forward-slashes-escaped
    return json.dumps( recursive_unicode(value) ).replace( "</", "<\\/" )

def json_decode(value):
    """Returns Python objects for the given JSON string."""
    return json.loads( to_basestring(value) )


