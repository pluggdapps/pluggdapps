# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

from   copy import deepcopy

import pluggdapps.utils          as h
from   pluggdapps.const          import CONTENT_IDENTITY
from   pluggdapps.plugin         import Plugin, implements
from   pluggdapps.web.interfaces import IHTTPNegotiator

class HTTPNegotiator( Plugin ):
    """Plugin handle server side negotiation. Gather client side negotiable
    information using following rules,

    * Use ``accept`` header from http request. If not available assume that any
      type of media encoding is acceptable by client.
    * Use ``accept_charset`` from http request. If not available assume that
      any character encoding is acceptable by client.
    * Use ``accept_encoding`` from http request. If not available assume
      `identity` coding.
    * Use ``accept_language`` from http request. If not available assume any
      language is acceptable by client.

    If a configured variant matches any of the combination supported by
    client, pick that variant and return the same. Otherwise return None.
    """
    implements( IHTTPNegotiator )
    
    #---- IHTTPNegotiator interface methods

    def negotiate( self, request, variants ):
        """:meth:`pluggdapps.plugin.ISettings.normalize_settings` interface
        method."""

        cltbl = self._compile_client_negotiation( request )
        variants_ = []
        for viewd in variants :
            self._variant_keys( viewd )
            q = max( cltbl.get( k, 0.0 ) for k in viewd['_http_negotiator'] )
            variants_.append(( viewd, q )) if q else None
        variants_ = sorted( variants_, key=lambda x : x[1], reverse=True )
        return variants_[0][0] if variants_ else None

    #-- local methods.

    def _variant_keys( self, viewd ):
        if '_http_negotiator' not in viewd : 
            fn = lambda x : (x,)
            typ, subtype = viewd['media_type'].split('/', 1)
            keys = [ (viewd['media_type'],), ('%s/*'%typ,), ('*/*',) ]
            keys = [ x+y
                for x in keys for y in map( fn, [viewd['charset'], '*']) ]
            keys = [ x+y
                for x in keys 
                for y in map(fn, [viewd['content_coding'], CONTENT_IDENTITY]) ]
            keys = [ x+y
                for x in keys 
                for y in map( fn, [viewd['language'], '*']) ]
            viewd['_http_negotiator'] = keys
        return viewd['_http_negotiator']

    def _compile_client_negotiation( self, request ):
        hs = [ request.headers.get( 'accept', b'' ),
               request.headers.get( 'accept_charset', b'' ),
               request.headers.get( 'accept_encoding', b'' ),
               request.headers.get( 'accept_language', b'' ),
             ]
        accept = h.parse_accept( hs[0] ) or [('*/*', 1.0, b'')]
        accchr = h.parse_accept_charset( hs[1] ) or [('*', 1.0)]
        accenc = h.parse_accept_encoding( hs[2] ) or [(CONTENT_IDENTITY, 1.0)]
        acclan = h.parse_accept_language( hs[3] ) or [('*', 1.0)]

        ad = { mt : q for mt, q, params in accept }
        bd = { (a, ch) : aq*q for ch, q in accchr for a, aq in ad.items() }
        cd = { b+(enc,) : bq*q for enc, q in accenc for b, bq in bd.items() }
        tbl = {}
        for ln, q in acclan :
            zd, yd = {}, deepcopy( cd )
            for part in ln.split('-') :
                yd = { k+(part,) : cq for k, cq in yd.items() }
                zd.update( yd )
            tbl.update({ k : cq*q for k, cq in zd.items() })
        return tbl

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        """:meth:`pluggdapps.plugin.ISettings.default_settings` interface
        method."""
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        """:meth:`pluggdapps.plugin.ISettings.normalize_settings` interface
        method."""
        return sett


_default_settings = h.ConfigDict()
_default_settings.__doc__ = "Plugin handle server side negotiation. "
