# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import hashlib

import pluggdapps.utils             as h
from   pluggdapps.plugin            import implements, Plugin
from   pluggdapps.web.webinterfaces import IHTTPEtag

class HTTPEtag( Plugin ):
    implements( IHTTPEtag )

    def etag( response, weak=False ):
        hasher = hashlib.sha1()
        [ hasher.update(x) for x in response.data ]
        return '"%s"' % hasher.hexdigest()

