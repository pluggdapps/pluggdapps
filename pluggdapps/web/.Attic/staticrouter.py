# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import re
from   copy import deepcopy

import pluggdapps.utils             as h
from   pluggdapps.const             import URLSEP, CONTENT_IDENTITY
from   pluggdapps.plugin            import Plugin, implements, plugincall
from   pluggdapps.web.webinterfaces import IHTTPRouter, IHTTPResource, \
                                           IHTTPView, IHTTPResponse
# Notes :
#   - An Allow header field MUST be present in a 405 (Method Not Allowed)
#     response.

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for url-routing plugin using pattern matching."""

_default_settings['defaultview']  = {
    'default' : 'pluggdapps.web.views.HTTPNotFound',
    'types'   : (str,),
    'help'    : "Use this :class:`IHTTPView` view callable plugin to generate "
                "a response for request that can't be resolved into a valid "
                "view-callable."
}
_default_settings['negotiate_content']  = {
    'default' : False,
    'types'   : (bool,),
    'help'    : "Do content-negotiation when more than one representation is "
                "available for the same resource."
}


class StaticRouter( Plugin ):
    """IHTTPRouter plugin to route request based on URL pattern matching."""

    implements( IHTTPRouter )

    def onboot( self ):
        """:meth:`pluggapps.web.webinterfaces.IHTTPRouter.onboot` interface
        method."""
        self['defaultview'] = plugincall(
            self['defaultview'],
            lambda:self.query_plugin(IHTTPView, self['defaultview'], name, None)
        )

    def add_view( self, name, pattern, view, **kwargs ):
        raise Exception( "This method is not applicable" )

    def route( self, request ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPRouter.route` interface
        method.
        """
        resp = request.response
        c = resp.context
        variants = []
        for name, viewd in self.views.items() :
            path = request.uriparts['path']
            m = viewd['compiled_pattern'].match( path )
            variants.append( (name, viewd, m) ) if m else None

        if variants :
            variant = self.negotiate( request, variants )
            if variant :
                name, viewd, m = variant
                resp.media_type = viewd['media_type']
                resp.charset = viewd['charset']
                resp.language = viewd['language']
                resp.content_coding = viewd['content_coding']
                request.matchdict = m.groupdict()
                request.view = plugincall(
                 viewd['view'], 
                 lambda:self.query_plugin(IHTTPView, viewd['view'], name, viewd)
                )
                # Call IHTTPResource plugin configured for this view callable.
                res = viewd['resource']
                res = plugincall(
                            res, lambda : self.query_plugin(IHTTPResource,res)
                      )
                res( request, c ) if res else None
                # If etag is available, compute and subsequently clear them.
                etag = c.etag.hashout( prefix='resp-' )
                c.setdefault( 'etag', etag ) if etag else None
                c.etag.clear()
            else :
                from pluggdapps.web.views import HTTPNotAcceptable
                request.matchdict = matchdict
                request.view = HTTPNotAcceptable
        else :
            request.matchdict = {}
            request.view = self['defaultview']

        if callable( request.view ) :   # Call the view-callable
            request.view( request, c )
            # If etag is available, compute and subsequently clear them.
            etag=c.etag.hashout(prefix='view-', joinwith=c.etag.pop('etag',''))
            c.setdefault( 'etag', etag ) if etag else None
            c.etag.clear()

    def negotiate( self, request, variants ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPRouter.negotiate` interface
        method."""
        negot_tbl = self._compile_client_negotiation( request )
        variants_ = []
        for name, viewd, m in variants :
            typ, subtype = viewd['media_type'].split('/', 1)
            keys = [ (viewd['media_type'],), ('%s/*'%typ,) ('*/*',) ]
            keys = [ x+y for x in keys 
                         for y in [ (viewd['charset'],), ('*',) ] ]
            keys = [ x+y for x in keys 
                         for y in [ (viewd['language'],), ('*',) ] ]
            keys = [ x+y for x in keys 
                         for y in [ (viewd['content_coding'],) ] ]
            q = max( negot_tbl.get( k, 0.0 ) for k in keys )
            variants_.append( (name, viewd, m, q) ) if q else None
        variants_ = sorted( variants_, key=lambda x : x[4], reverse=True )
        return variants_[0][:3] if variants_ else None


    def urlpath( self, request, name, **matchdict ):
        """This method is not applicable."""


    #---- Internal methods.

    def _compile_pattern( self, pattern ):
        """`pattern` is URL routing pattern.

        This method compiles the pattern in three different ways and returns
        them as a tuple of (regex, tmpl, redict)

        `regex`,
            A regular expression string that can be used to match incoming
            request-url to resolve view-callable.
        `tmpl`,
            A template formating string that can be used to generate URLs by
            apps.
        `redict`,
            A dictionary of variable components in path segment and optional
            regular expression that must match its value. This can be used for
            validation during URL generation.
        """
        regex, tmpl, redict = r'^', '', {}
        segs = pattern.split( URLSEP )
        while segs :
            seg = segs.pop(0)
            if not seg : continue
            regex, tmpl = (regex + URLSEP), (tmpl + URLSEP)
            prefx, _, name, reg, sufx = re_patt.match( seg ).groups()
            if name[0] == '*' :
                rempath = URLSEP.join( [seg] + segs )
                prefx, _, name, reg, sufx = re_patt.match( rempath ).groups()
                segs = []
            reg = reg and reg[1:]

            regex += prefx if prefx else r''
            if name and reg and sufx :
                regex += r'(?P<%s>%s(?=%s))%s' % (name, reg, sufx, sufx)
            elif name and reg :
                regex += r'(?P<%s>%s)' % (name, reg)
            elif name and sufx :
                regex += r'(?P<%s>.+(?=%s))%s' % (name, sufx, sufx)
            elif name :
                regex += r'(?p<%s>.+)' % (name,)
            elif sufx :
                regex += sufx
            tmpl += prefx if prefx else ''
            tmpl += '{' + name + '}' if name else ''
            tmpl += sufx if sufx else ''
            redict[ name ] = reg
        regex += '$'
        return regex, tmpl, redict

    def _compile_client_negotiation( self, request ):
        hs = [ request.headers.get( 'accept', None ),
               request.headers.get( 'accept_charset', None ),
               request.headers.get( 'accept_language', None ),
             ]
        accept = h.accept( hs[0] ) or [('*/*', 1.0, '')]
        accchr = h.accept_charset( hs[1] ) or [('*', 1.0)]
        accenc = h.accept_encoding( hs[3] ) or [(CONTENT_IDENTITY, 1.0)]
        acclan = h.accept_language( hs[2] ) or [('*', 1.0)]

        ad = { mt : q for mt, q, params in accept }
        bd = { (a, ch) : aq*q for ch, q in accchr for a, aq in ad.items() }
        cd = { (b, enc) : bq*q for enc, q in accenc for b, bq in bd.items() }
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
        method.
        """
        return _default_settings
