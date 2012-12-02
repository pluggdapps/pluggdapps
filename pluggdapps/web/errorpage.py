# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import traceback

import pluggdapps.utils             as h
from   pluggdapps.plugin            import implements, Plugin
from   pluggdapps.web.webinterfaces import IHTTPView

_default_settings = h.ConfigDict()
_default_settings.__doc__ = \
    ("Configuration settings for HTTPErrorPage implementing IHTTPView for "
     "error page interface.")

_default_settings['errortemplate']  = {
    'default' : '',
    'types'   : (str,),
    'help'    : "",
}

class HTTPErrorPage( Plugin ):
    implements( IHTTPView )

    def render( self, request, status_code, c ):
        """Use ``status_code``, typically an error code, and a collection of
        arguments ``kwargs`` to generate error page for ``request``. This is
        called as a result of :method:`IResponse.httperror` method.

        If this error was caused by an uncaught exception, an ``exc_info``
        triple can be passed as ``kwargs["exc_info"]``. Note that this
        exception may not be the "current" exception for purposes of
        methods like ``sys.exc_info()`` or ``traceback.format_exc``.
        """
        debug = request.app.globalsett['debug']
        response = request.response

        if debug and "exc_info" in kwargs :
            # in debug mode, try to send a traceback
            response.set_header( 'Content-Type', 'text/plain' )
            for line in traceback.format_exception( *kwargs["exc_info"] ):
                response.write(line)

        if self['errotemplate'] :
            conte

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        return _default_settings


