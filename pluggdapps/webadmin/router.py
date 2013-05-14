# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import pluggdapps.utils             as h
from   pluggdapps.web.matchrouter   import MatchRouter

from   pluggdapps.webadmin.views    import *

# Notes :
#   - An Allow header field MUST be present in a 405 (Method Not Allowed)
#     response.

class WebAdminRouter( MatchRouter ):
    """Router plugin deriving from :class:`MatchRouter` base class. Configures
    url patterns and static pages for webadmin application."""

    def onboot( self ):
        """:meth:`pluggapps.web.interfaces.IHTTPRouter.onboot` interface
        method."""
        super().onboot()
        self.add_view( 'staticfiles', '/static/*path', 
                       rootloc='pluggdapps:webadmin/static',
                       view='pluggdapps.staticview' )

        self.add_view( 'index', '/',
                       method=b'GET',
                       content_coding='gzip',
                       media_type='text/html',
                       view=get_index,
                     )

        self.add_view( 'htmlconfig1', '/config/{netpath}/{section}',
                       method=b'GET',
                       media_type='text/html',
                       content_coding='gzip',
                       view=get_html_config,
                     )

        self.add_view( 'updateconfig', '/config/{netpath}/{section}',
                       method=b'PUT',
                       media_type='application/json',
                       view=put_config )

        self.add_view( 'jsconfig1', '/config/{netpath}',
                       method=b'GET',
                       media_type='application/json',
                       view=get_json_config
                     )
        self.add_view( 'jsconfig2', '/config/{netpath}/{section}',
                       method=b'GET',
                       media_type='application/json',
                       view=get_json_config
                     )

        self.add_view( 'framedebug', '/debug/frame/{frameid}',
                       method=b'POST',
                       view=frame_debug )


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
_default_settings.__doc__ = WebAdminRouter.__doc__

