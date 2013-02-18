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
        if self['routemapper'] :
            fl = h.abspath_from_asset_spec( self['routemapper'] )
            if fl and isfile( fl ) :
                for vargs in eval( open( fl ).read() ) :
                    self.add_view( vargs.pop('name'), vargs.pop('pattern'), 
                                   **vargs )
            elif fl :
                raise Exception("Wrong configuration for routemapper : %r"%fl)
        else :
            self.add_view( 'staticmap1', '/*path', view='docrootview',
                           content_coding='gzip' )
            self.add_view( 'staticmap2', '/*path', view='docrootview' )

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
        sett['routemapper'] = sett['routemapper'].strip()
        return sett

_default_settings = h.ConfigDict()
_default_settings.__doc__ = DocRootRouter.__doc__

_default_settings['routemapper'] = {
    'default' : '',
    'types'   : (str,),
    'help'    : "Other than mapping static documents as web pages via "
                "``rootloc`` parameter, more view can be added via "
                "routemapper module, to be provided here in asset "
                "specification format. The module is expected to contain a "
                "list of dictionaries, where each dictionary will be passed "
                "to router's add_view() method as keyword argument, at boot "
                "time."
}

