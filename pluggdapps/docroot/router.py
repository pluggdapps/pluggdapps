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

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings for static website routing."""

_default_settings['routemapper'] = {
    'default' : '',
    'types'   : (str,),
    'help'    : "Filename along with its path, in asset specification "
                "format. Referred file contains route mapping information "
                "which will get transformed into add_view() calls during "
                "boot time."
}

class DocRootRouter( MatchRouter ):
    """IHTTPRouter plugin to route static web sites."""

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
