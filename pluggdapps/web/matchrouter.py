# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import re

import pluggdapps.utils             as h
from   pluggdapps.const             import URLSEP
from   pluggdapps.plugin            import Plugin, implements
from   pluggdapps.web.webinterfaces import IHTTPRouter, IHTTPResource, \
                                           IHTTPView, IHTTPResponse
# Notes :
#   - An Allow header field MUST be present in a 405 (Method Not Allowed)
#     response.

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for url-routing plugin using pattern matching."""

_default_settings['defaultview']  = {
    'default' : 'httpnotfound',
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
    """IHTTPRouter plugin to do request routing based on URL pattern
    matching."""

    implements( IHTTPRouter )

    def onboot( self ):
        self.views = {}

    def add_view( self, name, pattern, **kwargs ):
        self.views[ name ] = view = {}

        view['resource'] = kwargs.get( 'resource', None )
        view['view_callable'] = kwargs.get( 'view_callable', None )
        view['attr'] = kwargs.get( 'attr', None )

        view['pattern'] = pattern
        regex, tmpl, redict = self.compile_pattern( pattern )
        view['compiled_pattern'] = re.compile( regex )
        view['path_template'] = tmpl
        view['match_segments'] = redict

    def route( self, request, c ):
        for name, view in self.views.items() :
            path = request.uriparts['path']
            m = view['compiled_pattern'].match( path )
            if m == None : continue

            matchdict = m.groupdict()
            vcb = self.views[name]['view_callable']
            if isinstance( view, str ) :
                vcb = self.query_plugin( IHTTPView, vcb, name, view )

            if self.match_view( request, view, vcallable ):
                request.matchdict = matchdict
                request.view = vcb
                # Call IHTTPResource plugin configured for this view callable.
                res = view['resource']
                if isinstance(res, str) :
                    res = self.query_plugin( IHTTPResource, res )
                res( request, c ) if res else None
                break

            else :
                from pluggdapps.web.views import HTTPNotAcceptable
                request.matchdict = matchdict
                request.view = HTTPNotAcceptable

        else :
            request.matchdict = {}
            request.view = self.query_plugin( IHTTPView, self['defaultview'] )

        if request.view :   # Call the view-callable
            request.view( self, c )

    def urlpath( self, request, name, **matchdict ):
        view = self.views[ name ]
        return view['path_template'].format( matchdict )

    #---- Internal methods.

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

    def match_view( self, request, view, vcallable ):
        return True
        
    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings
