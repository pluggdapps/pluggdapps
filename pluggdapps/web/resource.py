# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import hashlib

import pluggdapps.utils             as h
from   pluggdapps.plugin            import implements, Plugin
from   pluggdapps.web.webinterfaces import IHTTPResource

class StaticResource( Plugin ):
    """Resource callable for static web-sites."""
    implements( IHTTPResource )

    #-- IHTTPResource interface methods

    def __call__( request, c ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResource.__call__ interface
        method."""

    def etag( self, response, weak=False ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPResource.etag interface
        method."""
        hasher = hashlib.sha1()
        [ hasher.update(x) for x in response.data ]
        return '"%s"' % hasher.hexdigest()

        # Automatically support ETags and add the Content-Length header of
        # non-chunked transfer-coding.
        if ( self.ischunked() == False and
             self.statuscode == b'200' and
             self.request.method in ("GET", "HEAD") ) :
            if "etag" not in self.headers :
                etagv = self.etag.compute( self ) if self.etag else None
                if etagv :
                    self.set_header( "etag", etag )
                    inm = self.request.headers.get( "if_none_match" )
                    if inm and inm.find( etag ) != -1:
                        self.write_buffer = None
                        self.statuscode= b'304'

        self.start_response = True
        return self._header_data( self.headers )
