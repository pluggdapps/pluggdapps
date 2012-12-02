# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import unittest
from   os.path              import dirname, join
from   pprint               import pprint

import pluggapps.utils      as h
from   pluggdapps.erlport   import ErlPort

baseini = join( dirname( __file__ ), 'tests', 'develop.ini' )

class TestPort( ErlPort ):

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )

    def logerror( self, formatstr, values ):
        print( formatstr, values )

erlport    = TestPort( descrs=(3,4) )

class TestConfig( unittest.TestCase ):

    def test_plugin2sec( self ):
        assert h.sec2plugin( h.plugin2sec( 'pluginname' )) == 'pluginname'
        assert is_plugin_section( h.plugin2sec( 'pluginname' ))

    def test_defaultsettings( self ):
        appdefaults, plugindefaults = pluggdapps.config.defaultsettings()
        # Apps
        assert 'webapp:webapp' in appdefaults
        assert 'webapp:rootapp' in appdefaults
        # Plugins
        assert 'plugin:baseresource' in plugindefaults
        assert 'plugin:commandcommands' in plugindefaults
        assert 'plugin:commandconfig' in plugindefaults
        assert 'plugin:commandls' in plugindefaults
        assert 'plugin:commandmounts' in plugindefaults
        assert 'plugin:commandserve' in plugindefaults
        assert 'plugin:commandunittest' in plugindefaults
        assert 'plugin:httpcookie' in plugindefaults
        assert 'plugin:httprequest' in plugindefaults
        assert 'plugin:httpresponse' in plugindefaults
        assert 'plugin:plugin' in plugindefaults

    def test_loadsettings( self ):
        from  pluggdapps.platform import settings
        assert 'pluggdapps' in settings
        assert 'mountloc' in settings
        assert 'plugin:baseresource' in settings
        assert 'plugin:commandcommands' in settings
        assert 'plugin:commandconfig' in settings
        assert 'plugin:commandls' in settings
        assert 'plugin:commandmounts' in settings
        assert 'plugin:commandserve' in settings
        assert 'plugin:commandunittest' in settings
        assert 'plugin:httpcookie' in settings
        assert 'plugin:httprequest' in settings
        assert 'plugin:httpresponse' in settings
        assert 'plugin:plugin' in settings

        for k, sett in settings.items() :
            if isinstance(k, tuple) :
                if k[0] == 'webapp:webapp' :
                    webappsett = sett
                if k[0] == 'webapp:rootapp' :
                    rootappsett = sett
        assert webappsett
        assert rootappsett

        assert settings['mountloc']['test'] == 'this'
        assert settings['pluggdapps']['test'] == 'that'
        assert settings['plugin:httprequest']['IHTTPCookie'] == 'httpcookie'
        assert settings['plugin:httpresponse']['IHTTPCookie'] == 'newcookie'

        assert settings['plugin:commandserve'] == \
                    webappsett['plugin:commandserve']
        assert settings['plugin:commandserve'] == \
                    rootappsett['plugin:commandserve']
        assert settings['plugin:commandcommands']['command_width'] == 18
        assert settings['plugin:commandcommands']['test'] == 'this'

        assert 'webapp:rootapp' in rootappsett
        assert rootappsett['webapp:rootapp']['IHTTPRouter'] == 'routeandmatch'
        assert rootappsett['plugin:httprequest']['IHTTPCookie'] == 'httpcookie'
        assert rootappsett['plugin:httpresponse']['IHTTPCookie'] == 'newcookie'
        assert rootappsett['plugin:httprequest']['test'] == 'this'

        assert 'webapp:webapp' in webappsett
        assert webappsett['webapp:webapp']['IHTTPResponse'] == 'newresponse'
        assert webappsett['plugin:httprequest']['IHTTPCookie'] == 'newcookie'
        assert webappsett['plugin:httpresponse']['IHTTPCookie'] == 'newcookie'
        assert webappsett['plugin:httprequest']['test'] == 'this'


if __name__ == '__main__' :
    unittest.main()
