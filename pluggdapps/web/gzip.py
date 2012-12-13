# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy


import gzip
from   io   import BytesIO, StringIO

import pluggdapps.utils             as h
from   pluggdapps.plugin            import Plugin, implements
from   pluggdapps.web.webinterfaces import IHTTPOutBound

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for Gzip transformer on response entity."

_default_settings['level']  = {
    'default' : 6,
    'types'   : (int,),
    'help'    : "Compression level while applying gzip."
}

class GZipOutBound( Plugin ) :
    """Out-bound transformer to compress response entity using gzip
    compression technology."""

    implements( IHTTPOutBound )

    def transform( self, request, data, finishing=True ):
        resp = request.response
        ctype = resp.headers.get( 'content_type', b'' )
        cenc  = resp.headers.get( 'content_encoding', None )

        # Compress only if content-type is 'text/*' or 'application/*'
        if ( data and resp.content_coding == 'gzip' and
             (ctype.startswith(b'text/') or ctype.startswith(b'application/'))
             and (b'zip' not in ctype) ) :
            resp.add_header( 'content_encoding', 'gzip' )
            data = self._gzip( data )
            if resp.ischunked() == False :
                resp.set_header( 'content_length', str( len(data) ))
                etag = resp.headers.get( 'etag', '' )
                resp.set_header( 'etag', etag[:-1] + b';gzip"' ) \
                        if etag else None

        if resp.ischunked() == False :
            resp.set_header( 'content_length', len( data ))
        return data

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
