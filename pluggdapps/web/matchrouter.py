# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import re

import pluggdapps.utils             as h
from   pluggdapps.const             import URLSEP
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

re_patt = re.compile( r'([^{]+)?'
                      r'(\{([a-z][a-z0-9]*)(,(?:[^\\]|\\.)*)?\})?'
                      r'(.+)?' )
          # prefix, _, name, regex, sufx

class MatchRouter( Plugin ):
    """IHTTPRouter plugin to router request based on URL pattern matching."""

    implements( IHTTPRouter )

    views = {}
    """Dictionary of view-names to view-callables and its predicates,
    typically added via add_view() interface method."""

    def onboot( self ):
        """:meth:`pluggapps.web.webinterfaces.IHTTPRouter.onboot` interface
        method."""
        self.views = {}

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

        ``resource``,
            A plugin name or plugin instance implementing
            :class:`IHTTPResource` interface, or just a plain python callable.
            What ever the case, please do go through the :class:`IHTTPResource`
            interface specification before authoring a resource-callable.

        ``view``,
            A plugin name or plugin instance implementing :class:`IHTTPView`
            interface, or just a plain python callable or a string that
            imports a callable object. What ever the case, please do go 
            through the :class:`IHTTPView` interface specification before 
            authoring a view-callable.

        ``attr``,
            Callable method attribute for ``view`` plugin.
        """
        self.views[ name ] = view = {}

        view['resource'] = kwargs.get( 'resource', None )
        view['view'] = kwargs.get( 'view', None )
        view['attr'] = kwargs.get( 'attr', None )

        view['pattern'] = pattern
        regex, tmpl, redict = self._compile_pattern( pattern )
        view['compiled_pattern'] = re.compile( regex )
        view['path_template'] = tmpl
        view['match_segments'] = redict

    def route( self, request, c ):
        """:meth:`pluggdapps.web.webinterfaces.IHTTPRouter.route` interface
        method.
        """
        for name, viewd in self.views.items() :
            path = request.uriparts['path']
            m = viewd['compiled_pattern'].match( path )
            if m == None : continue

            matchdict = m.groupdict()
            view = viewd['view']
            vcb = plugincall(
                    view, 
                    lambda : self.query_plugin( IHTTPView, view, name, viewd )
                  )
            if self._match_view( request, viewd, vcb ):
                request.matchdict = matchdict
                request.view = vcb
                # Call IHTTPResource plugin configured for this view callable.
                res = viewd['resource']
                res = plugincall(
                            res, lambda : self.query_plugin(IHTTPResource,res)
                      )
                res( request, c ) if res else None
                break

            else :
                from pluggdapps.web.views import HTTPNotAcceptable
                request.matchdict = matchdict
                request.view = HTTPNotAcceptable

        else :
            request.matchdict = {}
            view = self['defaultview']
            vcb = plugincall(
                    view,
                    lambda : self.query_plugin( IHTTPView, view, name, None )
                  )
            request.view = vcb

        if request.view :   # Call the view-callable
            request.view( request, c )

    def urlpath( self, request, name, **matchdict ):
        """Generate url path for request using view-patterns. Return a string
        of URL-path, with query and anchore elements.

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

    def _match_view( self, request, view, vcallable ):
        return True
        
    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        """:meth:`pluggdapps.plugin.ISettings.default_settings` interface
        method.
        """
        return _default_settings
