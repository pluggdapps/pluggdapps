# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import logging, re

from pluggdapps.const import URLSEP
from pluggdapps.plugin import interface
from pluggdapps.interfaces import IRouter
from pluggdapps.views import HTTPNotFound
import pluggdapps.utils as h

log = logging.getLogger( __name__ )

class BaseMixin( object ):

    def __init__( self, *args, **kwargs ):
        self.segment = None
        self.defaultview = HTTPNotFound
        self.traversals = {}
        self.views = {}

    def onboot( self, settings ):
        return settings

    def genpath( self, request, name, *traverse, **matchdict ) :
        if traverse :
            if self.traversals == {} :
                e = 'Traversals are not defined for this router, %r' % self
                h.Error( e )
            for segment, router in self.traversals.items() :
                if segment != traverse[0] : continue
                if traverse[1:] :
                    path = router.genpath( request, traverse[1:] )
                    return URLSEP + traverse[0] + URLSEP + path
            else :
                e = 'Cannot make path for %r %r %r' % (name,traverse,matchdict)
                raise h.Error( e )
        else :
            if self.views == {} :
                e = 'View patters are not defined for this router, %r' % self
                h.Error( e )
            if 'remains' in matchdict :
                matchdict['remains'] = URLSEP.join( matchdict['remains'] )
            tmpl = self.views[name]['path_template']
            return tmpl.format( **matchdict )


    def fetchview( self, request, c ):
        view = self.lookup_traversal( request, c )
        if view == None :
            view = self.lookup_view( request, c )
        return view


class TraverseMixin( BaseMixin ):
    """Provide necessary method to handle url routing through traversal."""

    def onboot( self, settings ):
        super().onboot( settings )

        # If an interface is configured for this router, then fetch all the
        # plugins implementing them and query and initialize them for this 
        # path-segment-level.
        traversewith, routers = self['traversewith'], []
        if traversewith :
            interf = interface( traversewith )
            routers = query_plugins( self.app, interf )
        for router in routers :
            if router.segment == None :
                raise h.Error(
                    ("Router %r for interface %r does not have "
                     "segment attribute") % (router, interf)
                )
            router.onboot( settings )
            self.traversals[router.segment] = router

        # If a router is configured for every segment name, then query and
        # initialize them for the corresponding segment name.
        segments = h.settingsfor( 'traverse.', self )
        for segment, routername in segments :
            router = query_plugin( self.app, IRouter, routername )
            router.segment = segment
            router.onboot( settings )
            self.traversals[segment] = router

    def lookup_traversal( self, request, c ):
        try : # Probe for current segment and remaining segment
            _, currseg, remseg = request.resolve_path.split( URLSEP, 2 )
        except :
            try : # If not, probe for current segment.
                _, currseg = request.resolve_path.split( URLSEP, 1 )
            except :
                return None

        if not currseg : return None

        # There is a current segment available, check for matching traversals
        for router in self.traversals :
            if router.segment == currseg :
                request.traversed.append( router )
                request.resolve_path = URLSEP + remseg if remseg else ''
                break
        else :
            router = None

        view = router.route( request, c ) if router else None
        return view


class MatchMixin( BaseMixin ):
    """Provide necessary method to handle url routing pattern matching."""

    def onboot( self, settings ):
        super().onboot( settings )

    def lookup_view( self, request, c ):
        for name, view in self.views :
            regc = view['compiled_pattern']
            m = regc.match( request.resolve_path )

            if m == None : continue

            request.matchrouter = self
            request.matchdict = m.groupdict()
            suffix = request.matchdict.get( h.ROUTE_PATH_SUFFIX, None )
            if suffix :
                suffix = suffix.split( URLSEP )
                request.matchdict[ h.ROUTE_PATH_SUFFIX ] = suffix
            request.view_name = name
            cb = view['view_callable']
            if isinstance( cb, str ):
                v = query_plugin( self.app, IController, cb )
            elif callable(cb) :
                v = cb
            else:
                raise h.Error( 'Callable not resolved for %r', name )
            return v
        return None

    def add_view( self, name, **kwargs ):
        self.views[name] = view = {}
        pattern = kwargs['pattern']
        view['resource'] = kwargs.get( 'resource', None )
        view['xhr'] = kwargs.get( 'xhr', None )
        view['method'] = kwargs.get( 'method', None )
        view['path_info'] = kwargs.get( 'path_info', None )
        view['params'] = kwargs.get( 'params', None )
        view['headers'] = kwargs.get( 'headers', None )
        view['accept'] = kwargs.get( 'accept', None )
        view['view_callable'] = kwargs.get( 'view_callable', None )
        view['attr'] = kwargs.get( 'attr', None )
        view['permission'] = kwargs.get( 'permission', None )
        view['pattern'] = pattern
        regex, tmpl =self._make_regex_tmpl( pattern )
        view['compiled_pattern'] = re.compile( regex )
        view['path_template'] = tmpl

    re_name = re.compile( r"([^{]*)({[^{}]+})?(.+)?" )
    def _make_regex_tmpl( self, pattern ):
        segs = pattern.split( URLSEP )
        regex, tmpl = r'^', ''
        for seg in segs :
            if not seg : continue
            regex, tmpl = (regex + URLSEP), (tmpl + URLSEP)
            prefix, name, suffix = re_name.match( seg ).groups()
            if name :
                name = name[1:-1]
            try :
                name, patt = name.split(':')
            except :
                patt = None
            regex += prefix if prefix else ''
            if name and patt :
                regex += '(?P<%s>%s)' % (name, patt)
            elif patt :
                regex += '(%s)' % patt
            elif name and suffix :
                regex += '(?P<%s>.+(?=%s))' % (name, suffix)
            elif name and name[0] == '*' :
                regex += '(?P<%s>.+)' % name[1:]
            elif name :
                regex += '(?P<%s>[^/]+)' % name
            regex += suffix if suffix else ''
            tmpl += suffix + '{' + name.rstrip('*') + '}' + prefix
        regex += '$'
        return regex, tmpl

