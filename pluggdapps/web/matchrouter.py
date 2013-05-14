# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import re
from   copy     import deepcopy
from   os.path  import isfile

import pluggdapps.utils          as h
from   pluggdapps.const          import URLSEP, CONTENT_IDENTITY
from   pluggdapps.plugin         import Plugin, implements, isplugin
from   pluggdapps.web.interfaces import IHTTPRouter, IHTTPResource, IHTTPView, \
                                        IHTTPNegotiator

# Notes :
#   - An Allow header field MUST be present in a 405 (Method Not Allowed)
#     response.

re_patt = re.compile( r'([^{]+)?(\{.+\})?([^}]+)?' )
          # prefix, { interpolater }, suffix

class MatchRouter( Plugin ):
    """Plugin to resolve HTTP request to a view-callable by matching patterns
    on request-URL. Refer to :class:`pluggdapps.web.interfaces.IHTTPRouter`
    interface spec. to understand the general intent and purpose of this
    plugin. On top of that, this plugin also supports server side HTTP content
    negotiation.
    
    When creating a web application using pluggdapps, developers must
    implement a router class, a plugin, implementing
    :class:`pluggdapps.web.interfaces.IHTTPRouter` interfaces. The general
    thumb rule is to derive their router class from one of the base routers
    defined under :mod:`pluggdapps.web` package. :class:`MatchRouter` is one
    such base class. When an application derives its router from this base
    class, it can override :meth:`onboot` method and call :meth:`add_view` to
    add view representations for matching resource.

    This router plugin adheres to HTTP concepts like resource, representation
    and views. As per the nomenclature, a resource is always identified by
    request-URL and same resource can have any number of representation. View
    is a callable entity that is capable of generating the desired
    representation. Note that a web page that is encoded with `gzip`
    compression is a different representation of the same resource that does
    not use `gzip` compression.

    Instead of programmatically configuring URL routing, it is possible to
    configure them using a mapper file. Which is a python file containing a
    list of dictionaries where each dictionary element will be converted to
    add_view() method call during onboot().
    
    **map file specification,**

    .. code-block:: python
        :linenos:

        [ { 'name'             : <variant-name as string>,
            'pattern'          : <regex pattern-to-match-with-request-URL>,
            'view'             : <view-callable as string>,
            'resource'         : <resource-name as string>,
            'attr'             : <attribute on view callable, as string>,
            'method'           : <HTTP request method as byte string>,
            'media_type'       : <content-type as string>,
            'language'         : <language-string as string>,
            'charset'          : <charset-string as string>,
            'content_coding'   : <content-coding as comma separated values>,
            'cache_control'    : <response header value>,
            'rootloc'          : <path to root location for static documents>,
          },
          ...
        ]
    """

    implements( IHTTPRouter )

    views = {}
    """Dictionary of view-names to view-callables and its predicates,
    typically added via add_view() interface method."""

    viewlist = []
    """same as views.items() except that this list will maintain the order in
    which the views where added. The same order will be used while resolving
    the request to view-callable."""

    negotiator = None
    """:class:`pluggdapps.web.interface.IHTTPNegotiator` plugin to handle HTTP
    negotiation."""

    def onboot( self ):
        """:meth:`pluggapps.web.interfaces.IHTTPRouter.onboot` interface
        method. Deriving class must override this method and use
        :meth:`add_view` to create router mapping."""
        self.views = {}
        self.viewlist = []
        self.negotiator = None
        if self['IHTTPNegotiator'] :
            self.negotiator = self.qp(IHTTPNegotiator, self['IHTTPNegotiator'])
        self['defaultview'] = h.string_import( self['defaultview'] )

        # Route mapping file is configured, populate view-callables from the
        # file.
        mapfile = self['routemapper']
        if mapfile and isfile( mapfile ) :
            for kwargs in eval( open( mapfile ).read() ) :
                name = kwargs.pop('name')
                pattern = kwargs.pop('pattern')
                self.add_view( name, pattern, **kwargs )

        elif mapfile :
            msg = "Wrong configuration for routemapper : %r" % mapfile
            raise Exception( msg )

    def add_view( self, name, pattern, **kwargs ):
        """Add a router mapping rule.
        
        ``name``,
            The name of the route. This attribute is required and it must be
            unique among all defined routes in a given web-application.

        ``pattern``,
            The pattern of the route. This argument is required. If pattern
            doesn't match the current URL, route matching continues.

        For EG,

        .. code-block:: python
            :linenos:

            self.add_view( 'article', 'blog/{year}/{month}/{date}' )


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
            If view-callable is a method on ``view`` object then supply this
            argument with a valid method name.

        ``method``,
            Request predicate. HTTP-method as byte string to be matched with
            incoming request.

        ``media_type``,
            Request predicate. Media type/subtype string specifying the
            resource variant. If unspecified, will be automatically detected
            using heuristics.

        ``language``,
            Request predicate. Language-range string specifying the resource
            variant. If unspecified, assumes webapp['language'] from
            configuration settings.

        ``charset``,
            Request predicate. Charset string specifying the resource variant.
            If unspecified, assumes webapp['encoding'] from configuration
            settings.

        ``content_coding``,
            Comma separated list of content coding that will be applied, in
            the same order as given, on the resource variant. Defaults to 
            `identity`.

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
        # Positional arguments.
        self.views[ name ] = view = {}
        view['name'] = name
        view['pattern'] = pattern
        regex, tmpl, redict = self._compile_pattern( pattern )
        view['compiled_pattern'] = re.compile( regex )
        view['path_template'] = tmpl
        view['match_segments'] = redict

        # Supported key-word arguments
        view['view'] = kwargs.pop( 'view', None )
        view['resource'] = kwargs.pop( 'resource', None )
        view['attr'] = kwargs.pop( 'attr', None )
        view['method'] = h.strof( kwargs.pop( 'method', None ))
        # Content Negotiation attributes
        view['media_type']=kwargs.pop('media_type', 'application/octet-stream')
        view['content_coding'] = kwargs.pop('content_coding',CONTENT_IDENTITY)
        view['language'] = kwargs.pop( 'language', self.webapp['language'] )
        view['charset'] = kwargs.pop( 'charset', self.webapp['encoding'] )
        
        # Content Negotiation attributes
        view.update( kwargs )
        self.viewlist.append( (name, view) )


    def route( self, request ):
        """:meth:`pluggdapps.web.interfaces.IHTTPRouter.route` interface
        method.

        Three phases of request resolution to view-callable,

        * From configured list of views, filter out views that maps to same
          request-URL.
        * From the previous list, filter the variants that match with request
          predicates.
        * If content negotiation is enable, apply server-side negotiation
          algorithm to single out a resource variant.

        If than one variant remains at the end of all three phases, then pick
        the first one in the list. And that is why the sequence in which
        :meth:`add_view` is called for each view representation is important.

        If ``resource`` attribute is configured on a view, it will be called
        with ``request`` plugin and ``context`` dictionary. Resource-callable
        can populate the context with relavant data that will subsequently 
        be used by the view callable, view-template etc. Additionally, if a
        resource callable populates the context dictionary, it automatically
        generates the etag for data that was populated through ``c.etag``
        dictionary. Populates context with special key `etag` and clears
        ``c.etag`` before sending the context to view-callable.
        """
        resp = request.response
        c = resp.context

        # Three phases of request resolution to view-callable
        matches = self._match_url( request, self.viewlist )
        variants = self._match_predicates( request, matches )
        if self.negotiator :
            variant = self.negotiator.negotiate( request, variants )
        elif variants :     # First come first served.
            variant = variants[0]
        else :
            variant = None

        if variant :        # If a variant is resolved
            name, viewd, m = variant['name'], variant, variant['_regexmatch']
            resp.media_type = viewd['media_type']
            resp.charset = viewd['charset']
            resp.language = viewd['language']
            resp.content_coding = viewd['content_coding']
            request.matchdict = m.groupdict()

            # Call IHTTPResource plugin configured for this view callable.
            resource = self._resourceof( request, viewd )
            resource( request, c ) if resource else None

            # If etag is available, compute and subsequently clear them.
            etag = c.etag.hashout( prefix='res-' )
            c.setdefault( 'etag', etag ) if etag else None
            c.etag.clear()

            request.view = self._viewof( request, name, viewd )

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
        method.
        
        Generate url path for request using view-patterns. Return a string of
        URL-path, with query and anchore elements.

        ``name``,
            Name of the view pattern to use for generating this url

        ``matchdict``,
            A dictionary of variables in url-patterns and their corresponding
            value string. Every route definition will have variable (aka
            dynamic components in path segments) that will be matched with
            url. If matchdict contains the following keys,

            `_query`, its value, which must be a dictionary similar to 
            :attr:`pluggdapps.web.interfaces.IHTTPRequest.getparams`, will be
            interpreted as query parameters and encoded to query string.

            `_anchor`, its value will be attached at the end of the url as
            "#<_anchor>".
        """
        view = self.views[ name ]
        query = matchdict.pop( '_query', None )
        fragment = matchdict.pop( '_anchor', None )
        path = view['path_template'].format( **matchdict )
        return h.make_url( None, path, query, fragment )

    def onfinish( self, request ):
        """:meth:`pluggdapps.web.interfaces.IHTTPRouter.onfinish` interface
        method.
        """
        pass

    #-- Local methods.

    def _viewof( self, request, name, viewd ):
        """For resolved view ``viewd``, fetch the view-callable."""
        v = viewd['view']
        self.pa.logdebug( "%r view callable: %r " % (request.uri, v) )
        if isinstance(v, str) and isplugin(v) :
            view = self.qp( IHTTPView, v, name, viewd )
        elif isinstance( v, str ):
            view = h.string_import( v )
        else :
            view = v
        return getattr( view, viewd['attr'] ) if viewd['attr'] else view

    def _resourceof( self, request, viewd ):
        """For resolved view ``viewd``, fetch the resource-callable."""
        res = viewd['resource']
        self.pa.logdebug( "%r resource callable: %r " % (request.uri, res) )
        if isinstance( res, str ) and isplugin( res ) :
            return self.qp( IHTTPResource, res )
        elif isinstance( res, str ) :
            return h.string_import( res )
        else :
            return res

    def _match_url( self, request, viewlist ):
        """Match view pattern with request url and filter out views with
        matching urls."""
        matches = []
        for name, viewd in viewlist :  # Match urls.
            m = viewd['compiled_pattern'].match( request.uriparts['path'] )
            if m :
                viewd = dict( viewd.items() )
                viewd['_regexmatch'] = m
                matches.append( viewd )
        return matches

    def _match_predicates( self, request, matches ):
        """Filter matching views, whose pattern matches with request-url,
        based on view-predicates. 
        
        TODO: More predicates to be added."""
        variants = []
        for viewd in matches :
            x = True
            if viewd['method'] != None :
                x = x and viewd['method'] == h.strof( request.method )
            variants.append( viewd ) if x else None

        return variants

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
        x = sett['routemapper'].strip() 
        sett['routemapper'] = h.abspath_from_asset_spec(x) if x else x
        return sett


_default_settings = h.ConfigDict()
_default_settings.__doc__ = (
    "Plugin to resolve HTTP request to a view-callable by matching patterns "
    "on request-URL. On top of that, this plugin also supports server side "
    "HTTP content negotiation." )

_default_settings['defaultview']  = {
    'default' : 'pluggdapps.web.views.HTTPNotFound',
    'types'   : (str,),
    'help'    : "Default view callable plugin. Will be used when request "
                "cannot be resolved to a valid view-callable."
}
_default_settings['IHTTPNegotiator']  = {
    'default' : 'pluggdapps.HTTPNegotiator',
    'types'   : (str,),
    'help'    : "If configured, will be used to handle server side http "
                "negotiation for best matching resource variant."
}
_default_settings['routemapper'] = {
    'default' : '',
    'types'   : (str,),
    'help'    : "Route mapper file in asset specification format. A python "
                "file containing a list of dictionaries, where each "
                "dictionary element will be converted to add_view() "
                "method-call on the router plugin."
}

