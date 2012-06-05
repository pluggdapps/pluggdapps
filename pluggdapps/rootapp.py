# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

import logging

from   pluggdapps.config        import ConfigDict
from   pluggdapps.application   import Application
import pluggdapps.utils         as h

log = logging.getLogger(__name__)

_default_settings = ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for root application."""


class RootApp( Application ):

    def onboot( self, settings ):
        super().onboot( settings )

    def shutdown( self, settings ):
        super().shutdown( settings )

    def start( self, request ):
        super().start( request )

    def onfinish( self, request ):
        super().onfinish( request )
        request.onfinish()

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        _default_settings.merge( super().default_settings() )
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        settings = super().normalize_settings( settings )
        return settings
