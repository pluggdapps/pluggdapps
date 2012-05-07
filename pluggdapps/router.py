# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

import logging

import pluggdapps.utils as h

log = logging.getLogger( __name__ )

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for url Router RouteMatch."

class RouteMatch( Plugin ):
    implements( IRouter )

    def __init__( self, *args, **kwargs ):
        self.router = None

    def onboot( self, settings ):
        """Override this."""

    def router( request, interface ):
        if self.router : return self.router

        segment = url.rstrip('/').split('/', 1)[0]
        if segment :
            self.router = query_plugin( request.app, interface, segment )
        else :
            log.error('Segments exhausted for resolving %r', interface )
        return self.router

    def match( self, request ):
        pass

    def add_route( self, *args, **kwargs ):
        pass


