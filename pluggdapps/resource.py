# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import logging

from   pluggdapps.config import ConfigDict
from   pluggdapps.plugin import Plugin
from   pluggdapps.core   import implements
from   pluggdapps.interfaces import IResource

log = logging.getLogger( __name__ )

_default_settings = ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for url Router RouteMatch."

class BaseResource( Plugin ):
    implements( IResource )

    def __call__( request, c ):
        c['title'] = 'Welcome to pluggdapps'


class StaticResource( BaseResource ):

    def __call__( request, c ):
        super().__call__( request, c )

