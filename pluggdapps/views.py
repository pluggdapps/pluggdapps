# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

def HTTPNotFound( request, c ):
    res = request.response
    res.set_status( 404 )
    res.write()
    res.flush()
    res.finish()

def HTTPServiceUnavailable( request, c ):
    res = request.response
    res.set_status( 503 )
    res.set_header( request.webapp.pa['retry_after'] )
    res.write()
    res.flush()
    res.finish()
