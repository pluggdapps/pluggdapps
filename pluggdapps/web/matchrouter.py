# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""
Site-variant map specification:
-------------------------------

This is a python module containing a list of dictionaries, where each
dictionary has a structure of,

{ 'name'             : <variant-name>,
  'pattern'          : <pattern-to-match-with-request-URL>,
  'resource'         : <resource-name>,
  'media_type'       : <content-type>,
  'language'         : <language-string>,
  'charset'          : <charset-string>,
  'content_coding'   : <content-coding-string>
}
"""

import re
from   copy import deepcopy
from   os.path import isfile

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
_default_settings['routemapper'] = {
    'default' : '',
    'types'   : (str,),
    'help'    : "Filename along with its path, in asset specification format.  "
                "Referred file contains route mapping information which will "
                "get transformed into add_view() calls during boot time."
}


re_patt = re.compile( r'([^{]+)?(\{.+\})?([^}]+)?' )
          # prefix, interpolater, suffix

class MatchRouter( Plugin ):
    """IHTTPRouter plugin to route request based on URL pattern matching."""

    implements( IHTTPRouter )

    views = {}
    """Dictionary of view-names to view-callables and its predicates,
    typically added via add_view() interface method."""

    def onboot( self ):
        """:meth:`pluggapps.web.webinterfaces.IHTTPRouter.onboot` interface
        method."""
        self.views = {}
        self['defaultview'] = plugincall(
            self['defaultview'],
            lambda:self.query_plugin(IHTTPView, self['defaultview'], name, None)
        )
        fl = h.abspath_from_asset_spec( self['routemapper'] )
        if fl and isfile( fl ) :
            [ self.add_view( vargs.pop('name'), vargs.pop('pattern'), **vargs )
              for vargs in eval( open( fl ).read() ) ]
        elif fl :
            raise Exception( "Wrong configuration for routemapper : %r" % fl )

    def add_view( self, name, pattern, **kwargs ):
        """Add a router mapping rule.
        
        ``name``,
            The name of the route. This attribute is required and it must be
            unique among all defined routes in a given web-application.

        ``pattern``,
            The pattern of the route like blog/{year}/{month}/{date}. This 
            argument is required. If the pattern doesn't match the current 
            URL, route matching continues.

        Optional key-word arguments,

        ``view``,
            A plugin name or plugin instance implementing :class:`IHTTPView`
            interface, or just a plain python callable or a string that
            imports a callable object. What ever the case, please do go 
            through the :class:`IHTTPView` interface specification before 
            authoring a view-callable.

        ``resource``,
            A plugin name or plugin instance implementing
            :class:`IHTTPResource` interface, or just a plain python callable.
            What ever the case, please do go through the :class:`IHTTPResource`
            interface specification before authoring a resource-callable.

        ``attr``,
            Callable method attribute for ``view`` plugin.

        ``media_type``,
            Media type/subtype string specifying the resource variant. If
            unspecified will be automatically detected using heuristics.

        ``language``,
            Language-range string specifying the resource variant. If
            unspecified defaults to webapp['language'] configuration settings.

        ``charset``,
            Charset string specifying the resource variant. If unspecified
            defaults to use webapp['encoding']

        ``content_coding``,
            Comma separated list of content coding that will be applied, in
            the same order as given, on the resource variant. Defaults to 
            'identity'.

        ``cache_control``,
            Cache-Control response header value to be used for the resource's
            variant.

        ``media_type``, ``language``, ``content_coding`` and ``charset``
        kwargs, if supplied, will be used during content negotiation.
        """
        self.views[ name ] = view = {}
        view['view'] = kwargs.pop( 'view', None )

        view['resource'] = kwargs.pop( 'resource', None )
        view['attr'] = kwargs.pop( 'attr', None )
        # Content Negotiation attributes
        view['media_type'] = kwargs.pop('media_type','application/octet-stream')
        view['content_coding'] = kwargs.pop('content_coding',CONTENT_IDENTITY)
        view['language'] = kwargs.pop( 'language', self.webapp['language'] )
        view['charset'] = kwargs.pop( 'charset', self.webapp['encoding'] )
        
        # Populate the remaining items.
        view.update( kwargs )

        view['pattern'] = pattern
        regex, tmpl, redict = self._compile_pattern( pattern )
        view['compiled_pattern'] = re.compile( regex )
        view['path_template'] = tmpl
        view['match_segments'] = redict

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
                vobj = plugincall(
                 viewd['view'], 
                 lambda:self.query_plugin(IHTTPView, viewd['view'], name, viewd)
                )
                request.view = getattr( vobj, viewd['attr'] ) \
                                    if viewd['attr'] else vobj
                # Call IHTTPResource plugin configured for this view callable.
                res = viewd['resource']
                if res :
                    res = plugincall(
                            res, lambda : self.query_plugin(IHTTPResource,res)
                          )
                    res( request, c )
                # If etag is available, compute and subsequently clear them.
                etag = c.etag.hashout( prefix='resp-' )
                c.setdefault( 'etag', etag ) if etag else None
                c.etag.clear()
            else :
                from pluggdapps.web.views import HTTPNotAcceptable
                request.view = HTTPNotAcceptable
        else :
            request.view = self['defaultview']

        if callable( request.view ) :   # Call the view-callable
            request.view( request, c )

    def negotiate( self, request, variants ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPRouter.negotiate` interface
        method."""
        negot_tbl = self._compile_client_negotiation( request )
        fn = lambda x : (x,)
        variants_ = []
        for name, viewd, m in variants :
            typ, subtype = viewd['media_type'].split('/', 1)
            keys = [ (viewd['media_type'],), ('%s/*'%typ,), ('*/*',) ]
            keys = [ x+y
                for x in keys 
                for y in map( fn, [viewd['charset'], '*']) ]
            keys = [ x+y
                for x in keys 
                for y in map(fn, [viewd['content_coding'], CONTENT_IDENTITY]) ]
            keys = [ x+y
                for x in keys 
                for y in map( fn, [viewd['language'], '*']) ]
            q = max( negot_tbl.get( k, 0.0 ) for k in keys )
            variants_.append( (name, viewd, m, q) ) if q else None
        variants_ = sorted( variants_, key=lambda x : x[3], reverse=True )
        return variants_[0][:3] if variants_ else None

    def urlpath( self, request, name, **matchdict ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPRouter.route` interface
        method. Generate url path for request using view-patterns. Return a
        string of URL-path, with query and anchore elements.

        ``name``,
            Name of the view pattern to use for generating this url

        ``matchdict``,
            A dictionary of variables in url-patterns and their corresponding
            value string. Every route definition will have variable (aka
            dynamic components in path segments) that will be matched with
            url. If matchdict contains the following keys,

            `_query`, its value, which must be a dictionary similar to 
            :attr:`IHTTPRequest.getparams`, will be interpreted as query
            parameters and encoded to query string.

            `_anchor`, its value will be attached at the end of the url as
            "#<_anchor>".
        """
        view = self.views[ name ]
        query = matchdict.pop( '_query', None )
        fragment = matchdict.pop( '_anchor', None )
        path = view['path_template'].format( matchdict )
        return h.make_url( None, path, query, fragment )


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
            part = segs.pop(0)
            if not part : continue
            if part[0] == '*' :
                part = URLSEP.join( [part] + segs )
                prefx, name, reg, sufx = None, part[1:], r'.*', None
                segs = []
            else :
                prefx, interp, sufx = re_patt.match( part ).groups()
                if interp :
                    try : name, reg = interp[1:-1].split(',', 1)
                    except : name, reg = interp[1:-1], None
                else :
                    name, reg = None, None

            regex += prefx if prefx else r''
            if name and reg and sufx :
                regex += r'(?P<%s>%s(?=%s))%s' % (name, reg, sufx, sufx)
            elif name and reg :
                regex += r'(?P<%s>%s)' % (name, reg)
            elif name and sufx :
                regex += r'(?P<%s>.+(?=%s))%s' % (name, sufx, sufx)
            elif name :
                regex += r'(?P<%s>.+)' % (name,)
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
               request.headers.get( 'accept_encoding', None ),
               request.headers.get( 'accept_language', None ),
             ]
        accept = h.accept( hs[0] ) or [('*/*', 1.0, '')]
        accchr = h.accept_charset( hs[1] ) or [('*', 1.0)]
        accenc = h.accept_encoding( hs[2] ) or [(CONTENT_IDENTITY, 1.0)]
        acclan = h.accept_language( hs[3] ) or [('*', 1.0)]

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
        method.
        """
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        """:meth:`pluggdapps.plugin.ISettings.normalize_settings` interface
        method.
        """
        sett['routemapper'] = sett['routemapper'].strip()
        return sett
