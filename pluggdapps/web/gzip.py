# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy


import gzip
from   io   import BytesIO

import pluggdapps.utils          as h
from   pluggdapps.plugin         import Plugin, implements
from   pluggdapps.web.interfaces import IHTTPOutBound

class GZipOutBound( Plugin ) :
    """Out-bound transformer to compress response entity using gzip
    compression technology."""

    implements( IHTTPOutBound )

    def transform( self, request, data, finishing=True ):
        resp = request.response
        ctype = resp.headers.get( 'content_type', b'' )
        cenc  = resp.headers.get( 'content_encoding', b'' )
        etag = resp.headers.get( 'etag', b'' )

        # Compress only if content-type is 'text/*' or 'application/*'
        if self._is_gzip( data, cenc, ctype, resp.statuscode ) :
            data = self._gzip( data )
            # etag is always double-quoted.
            resp.set_header( 'etag', etag[:-1] + b';gzip"' ) if etag else None
        else :
            enc = cenc.replace( b'gzip', b'' )
            resp.set_header('content_encoding', enc)
        return data

    def _is_gzip( self, data, enc, typ, status ):
        return ( bool(data) and
                 b'gzip' in enc and
                 (typ.startswith(b'text/') or 
                       typ.startswith(b'application/')) and
                 b'zip' not in typ )

    def _gzip( self, data ):
        buf = BytesIO()
        gzipper = gzip.GzipFile( 
                        mode='wb', compresslevel=self['level'], fileobj=buf)
        gzipper.write( data )
        gzipper.close()
        buf.seek(0)
        data = buf.getvalue()
        buf.close()
        return data

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        """:meth:`pluggdapps.plugin.ISettings.default_settings` interface
        method.
        """
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        """:meth:`pluggdapps.plugin.ISettings.normalize_settings` interface
        method.
        """
        sett['level'] = h.asint( sett['level'] )
        return sett


_default_settings = h.ConfigDict()
_default_settings.__doc__ = GZipOutBound.__doc__

_default_settings['level']  = {
    'default' : 6,
    'types'   : (int,),
    'help'    : "Compression level while applying gzip."
}

