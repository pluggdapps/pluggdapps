# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import pluggdapps.utils             as h
from   pluggdapps.plugin            import implements, Plugin
from   pluggdapps.web.webinterfaces import IResource

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for url Router RouteMatch."

class BaseResource( Plugin ):
    implements( IResource )

    def __call__( request, c ):
        c['title'] = 'Welcome to pluggdapps'


class StaticResource( BaseResource ):

    def __call__( self, request, c ):
        super().__call__( request, c )

