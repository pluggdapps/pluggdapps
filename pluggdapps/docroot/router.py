# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

from   os.path import isfile

import pluggdapps.utils             as h
from   pluggdapps.web.matchrouter   import MatchRouter

# Notes :
#   - An Allow header field MUST be present in a 405 (Method Not Allowed)
#     response.

class DocRootRouter( MatchRouter ):
    """IHTTPRouter plugin to map static documents as web pages. Supports gzip
    content coding on document resource. Implemented as part of docroot
    web-application."""

    def onboot( self ):
        """:meth:`pluggapps.web.interfaces.IHTTPRouter.onboot` interface
        method."""
        super().onboot()
        self.add_view( 'staticmap1', '/*path', view='pluggdapps.docrootview',
                       content_coding='gzip' )

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
_default_settings.__doc__ = DocRootRouter.__doc__
