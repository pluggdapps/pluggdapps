# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

from   random import choice
import unittest
import http.cookies
import datetime as dt

from   pluggdapps.plugin     import pluginname, query_plugins, query_plugin
from   pluggdapps.interfaces     import IWebApp
from   pluggdapps.platform       import Pluggdapps
from   pluggdapps.web.interfaces import IHTTPCookie


refheaders = {
'Cookie' : 'bcookie="v=2&95d39ed5-7853-4246-8a84-a00e00356edb";'
            '__qca=P0-452588846-1341819004642; visit="v=1&M";'
            'JSESSIONID="ajax:8780860854276913234"; X-LI-IDC=C1;'
            'srchId=cd05e5b2-7629-43ff-ae7b-a4889c786305-1;'
            'sdsc=22%3A1%2C1344608656947%7EMBR2%2C09byRCSQeB4V7UVfEv978u6rGx%2F8%3D;'
            'leo_auth_token="LIM:14006158:i:1344612685:4ded5e30ad24efc2873a61fbc7a40587fc485cc3";'
            '_leo_profile="u=14006158";'
            '_lipt=0_1TqoS8DLE0jRwXV5fH0zg7qzSLy4qn4Ytn93AknxRnx4FWw5ZALnVvqSzE3z3rk5xcPbTAb5GhfdHSYDwWEQBVhVvpfX5XR9vS6xH0sD_dTq11k4lh5dHyGHoHvrpsEJ088BDNYdHApra8xYaKGrv2CK7J8GQSHrXESyCnufEbwJlu1A87bo_j_hwVmsZ47p-6Nlz-2qs97iMdW5RRFF1V;'
            '__utma=23068709.1922354388.1341819003.1344517391.1344613437.5;'
            '__utmc=23068709;'
            '__utmz=23068709.1344408375.3.2.utmcsr=in.linkedin.com|utmccn=(referral)|utmcmd=referral|utmcct=/in/prataprc;'
            '__utmv=23068709.user; lang="v=2&lang=en-us&c="'
}

class TestIHTTPCookie( unittest.TestCase ):

    def test_plugins( self ):
        webapp = Pluggdapps.webapps['webapp']
        cookie_plugins = query_plugins( webapp, IHTTPCookie )
        assert 'httpcookie' in list( map( pluginname, cookie_plugins ))
        for cookp in cookie_plugins :
            cookies = cookp.parse_cookies( refheaders )
            assert 'bcookie' in cookies
            m = cookies['bcookie']
            assert m.key == 'bcookie'
            assert m.value == 'v=2&95d39ed5-7853-4246-8a84-a00e00356edb'
            cookies = cookp.set_cookie( cookies, 'hello', 'world',
                              expires=dt.datetime( 2012, 8, 13 ),
                              path="/for/this/path",
                              comment="some comment",
                              domain=".x.com",
                              max_age=10000,
                              secure=True,
                              version="1.1",
                              httponly=True
                      )
            s = cookies['hello'].output()
            assert cookies['hello'].value == 'world'
            assert 'expires=Mon, 13 Aug' in s
            assert 'Path=/for/this/path' in s
            assert 'Comment=some comment' in s
            assert 'Domain=.x.com' in s
            assert 'Version=1.1' in s
            assert 'Max-Age=10000' in s
            assert 'secure;' in s
            assert 'httponly;' in s
            
            # Signed value
            cookies['newname'] = cookp.create_signed_value( 'newname', 'world' )
            s = cookies['newname'].output()
            del cookies['newname']
            cookies.load( s )
            val = cookp.decode_signed_value( 
                    'newname', cookies['newname'].value )
            assert val == 'world'
