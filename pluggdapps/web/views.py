# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

def HTTPNotFound( request, c ):
    resp = request.response
    resp.set_status( b'404' )
    resp.flush( finishing=True )

def HTTPNotAcceptable( request, c ):
    resp = request.response
    resp.set_status( b'406' )
    resp.flush( finishing=True )

def HTTPServiceUnavailable( request, c ):
    resp = request.response
    resp.set_status( b'503' )
    resp.set_header( request.webapp.pa['retry_after'] )
    resp.flush( finishing=True )

def SplashPage( request, c ):
    resp = request.response
    resp.write( "hello world" )
    resp.flush( finishing=True )

