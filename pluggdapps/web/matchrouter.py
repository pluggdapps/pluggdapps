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

import pluggdapps.utils          as h
from   pluggdapps.const          import URLSEP, CONTENT_IDENTITY
from   pluggdapps.plugin         import Plugin, implements, isplugin
from   pluggdapps.web.interfaces import IHTTPRouter, IHTTPResource, \
                                        IHTTPView, IHTTPResponse
# Notes :
#   - An Allow header field MUST be present in a 405 (Method Not Allowed)
#     response.

re_patt = re.compile( r'([^{]+)?(\{.+\})?([^}]+)?' )
          # prefix, interpolater, suffix

class MatchRouter( Plugin ):
    """IHTTPRouter plugin to route request based on URL pattern matching."""

    implements( IHTTPRouter )

    views = {}
    """Dictionary of view-names to view-callables and its predicates,
    typically added via add_view() interface method."""

    viewlist = []
    """same as views.items() except that this list will maintain the order in
    which the views where added."""

    def onboot( self ):
        """:meth:`pluggapps.web.interfaces.IHTTPRouter.onboot` interface
        method."""
        self.views = {}
        self.viewlist = []
        self['defaultview'] = h.string_import( self['defaultview'] )

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

        ``method``,
            HTTP method string supported by the view. Eg. b'GET', b'PUT' etc.

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

        ``rootloc``,
            To add views for static files, use this attribute. Specifies the
            root location where static files are located. Note that when using
            this option, ``pattern`` argument must end with ``*path``.

        ``media_type``, ``language``, ``content_coding`` and ``charset``
        kwargs, if supplied, will be used during content negotiation.
        """
        self.views[ name ] = view = {}
        view['view'] = kwargs.pop( 'view', None )

        view['resource'] = kwargs.pop( 'resource', None )
        view['attr'] = kwargs.pop( 'attr', None )
        view['method'] = h.strof( kwargs.pop( 'method', None ))
        # Content Negotiation attributes
        view['media_type']=kwargs.pop('media_type', 'application/octet-stream')
        view['content_coding'] = kwargs.pop('content_coding',CONTENT_IDENTITY)
        view['language'] = kwargs.pop( 'language', self.webapp['language'] )
        view['charset'] = kwargs.pop( 'charset', self.webapp['encoding'] )
        
        # Populate the remaining items.
        view.update( kwargs )

        view['pattern'] = pattern
        regex, tmpl, redict = self.compile_pattern( pattern )
        view['compiled_pattern'] = re.compile( regex )
        view['path_template'] = tmpl
        view['match_segments'] = redict
        self.viewlist.append( (name, view) )

    def route( self, request ):
        """:meth:`pluggdapps.web.interfaces.IHTTPRouter.route` interface
        method.
        """
        resp = request.response
        c = resp.context

        # Three phases of request resolution to view-callable
        matches = self.match_url( request, self.viewlist )
        variants = self.match_predicates( request, matches )
        variant = self.negotiate( request, variants )

        if variant :
            name, viewd, m = variant
            resp.media_type = viewd['media_type']
            resp.charset = viewd['charset']
            resp.language = viewd['language']
            resp.content_coding = viewd['content_coding']
            request.matchdict = m.groupdict()

            # Call IHTTPResource plugin configured for this view callable.
            resource = self.resourceof( request, viewd )
            resource( request, c ) if resource else None

            # If etag is available, compute and subsequently clear them.
            etag = c.etag.hashout( prefix='resp-' )
            c.setdefault( 'etag', etag ) if etag else None
            c.etag.clear()

            request.view = self.viewof( request, name, viewd )

        elif matches :
            from pluggdapps.web.views import HTTPNotAcceptable
            request.view = HTTPNotAcceptable

        else :
            request.view = self['defaultview']

        if callable( request.view ) :   # Call the view-callable
            c['h'] = h
            request.view( request, c )

    def urlpath( self, request, name, **matchdict ):
        """:meth:`pluggdapps.web.interfaces.IHTTPRouter.route` interface
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
        path = view['path_template'].format( **matchdict )
        return h.make_url( None, path, query, fragment )


    #---- Internal methods.

    def match_url( self, request, viewlist ):
        """Match view pattern with request url and filter out views with
        matching urls."""
        matches = []
        for name, viewd in viewlist :  # Match urls.
            m = viewd['compiled_pattern'].match( request.uriparts['path'] )
            matches.append( (name, viewd, m) ) if m else None
        return matches

    def match_predicates( self, request, matches ):
        """Filter matching views, whose pattern matches with request-url,
        based on view-predicates"""
        variants = []
        for name, viewd, m in matches :
            x = True
            if viewd['method'] != None :
                x = x and viewd['method'] == h.strof( request.method )
            variants.append( (name, viewd, m) ) if x else None

        return variants

    def negotiate( self, request, variants ):
        """When the router finds that a resource (typically indicated by the
        request-URL) is multiple representations, where each representation is
        called a variant, it has to pick the best representation negotiated by
        the client. Negotiation is handled through attributes like media-type,
        language, charset and content-encoding. Returns the best matching
        variant from ``variants``. 

        ``request``,
            Plugin instance implementing :class:`IHTTPRequest` interface.

        Return matching variant.
        """
        if self['negotiate_content'] == False :
            return variants[0] if variants else None

        negot_tbl = self.compile_client_negotiation( request )

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

    def viewof( self, request, name, viewd ):
        """For resolved view ``viewd``, fetch the view-callable."""
        v = viewd['view']
        self.pa.logdebug( "%r view callable: %r " % (request.uri, v) )
        if isinstance( v, str ) and isplugin(v) :
            view = self.query_plugin( IHTTPView, v, name, viewd )
        elif isinstance( v, str ):
            view = h.string_import( v )
        else :
            view = v
        return getattr( view, viewd['attr'] ) if viewd['attr'] else view

    def resourceof( self, request, viewd ):
        """For resolved view ``viewd``, fetch the resource-callable."""
        res = viewd['resource']
        self.pa.logdebug( "%r resource callable: %r " % (request.uri, res) )
        if isinstance( res, str ) and isplugin( res ) :
            return self.query_plugin( IHTTPResource, res )
        elif isinstance( res, str ) :
            return h.string_import( res )
        else :
            return res

    def compile_pattern( self, pattern ):
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
        segs = list( filter( None, pattern.split( URLSEP )))
        while segs :
            regex += URLSEP
            tmpl += URLSEP
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

    def compile_client_negotiation( self, request ):
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
        method.
        """
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        """:meth:`pluggdapps.plugin.ISettings.normalize_settings` interface
        method.
        """
        return sett


_default_settings = h.ConfigDict()
_default_settings.__doc__ = MatchRouter.__doc__

_default_settings['defaultview']  = {
    'default' : 'pluggdapps.web.views.HTTPNotFound',
    'types'   : (str,),
    'help'    : "Default view callable plugin. Will be used when request "
                "cannot be resolved to a valid view-callable."
}
_default_settings['negotiate_content']  = {
    'default' : True,
    'types'   : (bool,),
    'help'    : "If True, then content-negotiation will be invoked when more "
                "than one representation is available for the same resource."
}

