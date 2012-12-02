# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import hashlib

import pluggdapps.utils             as h
from   pluggdapps.plugin            import implements, Plugin
from   pluggdapps.web.webinterfaces import IHTTPEtag

class HTTPEtag( Plugin ):
    """Compute etag based on hashlib.sha1 in python stdlib."""
    implements( IHTTPEtag )

    #-- IHTTPEtag interface methods

    def compute( self, response, weak=False ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPEtag.compute interface
        method."""
        hasher = hashlib.sha1()
        [ hasher.update(x) for x in response.data ]
        return '"%s"' % hasher.hexdigest()

