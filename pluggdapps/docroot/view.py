# -*- coding: utf-8 -*-

import pluggdapps.utils             as h


def SplashPage( request, c ):
    res = request.response
    res.write( "hello world" )
    res.flush( finished=True )
