# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import logging

log = logging.getLogger( __name__ )

def HTTPNotFound( request, c ):
    res = request.response
    res.set_status( 404 )
    res.write()
    res.flush()
    res.finish()

def HTTPServiceUnavailable( request, c ):
    res = request.response
    res.set_status( 503 )
    res.set_header( request.app.platform['retry_after'] )
    res.write()
    res.flush()
    res.finish()
