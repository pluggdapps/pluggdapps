# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy


def HTTPNotFound( request, c ):
    res = request.response
    res.set_status( 404 )
    res.flush( finishing=True )

def HTTPNotAcceptable( request, c ):
    res = request.response
    res.set_status( 406 )
    res.flush( finishing=True )

def HTTPServiceUnavailable( request, c ):
    res = request.response
    res.set_status( 503 )
    res.set_header( request.webapp.pa['retry_after'] )
    res.flush( finishing=True )

def SplashPage( request, c ):
    res = request.response
    res.write( "hello world" )
    res.flush( finishing=True )
