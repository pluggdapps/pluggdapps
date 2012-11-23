# -*- coding: utf-8 -*-

import pluggdapps.utils             as h


def SplashPluggdapps( request, c ):
    res = request.response
    res.write( "hello world" )
    res.flush( finished=True )
