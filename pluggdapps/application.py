# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import logging

from   pluggdapps.plugin     import Plugin, Interface, implements
from   pluggdapps.interfaces import IApplication

log = logging.getLogger(__name__)

class RootApplication( Plugin ):
    implements( IApplication )

    def boot( self, settings ):
        pass

    def start( self, request ):
        pass

    def router( self, request ):
        pass

    def finish( self, request ):
        pass

    def shutdown( self, settings ):
        pass
