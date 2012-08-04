import unittest
from   random import choice

from   pluggdapps.plugin    import *
from   pluggdapps.interface import \
        ICommand, IController, ICookie, IErrorPage, IRenderer, \
        IRequest, IResource, IResponse, IResponseTransformer, IRouter, \
        IServer, ISettings, IWebApp

class TestPlugin( unittest.TestCase ):

    def test_isimplement( self ):
        ls = query_plugin( None, ICommand, 'ls' )
        assert isimplement( ls, ICommand )
        assert isimplement( ls, ISettings )
        assert not isimplement( ls, IWebApp )

    def test_interfaces( self ):
        ref = [ ICommand, IController, ICookie, IErrorPage, IRenderer, IRequest,
                IResource, IResponse, IResponseTransformer, IRouter, IServer,
                ISettings, IWebApp ]
        assert sorted( interfaces() ) == sorted( ref )

    def test_interface( self ):
        assert interface( 'ICommand' ) == ICommand

    def test_plugin_info( self ):
        from pluggdapps.commands.ls import CommandLs
        ls = query_plugin( None, ICommand, 'ls' )
        x = plugin_info( 'commandls' )
        assert x['cls'] == CommandLs
        x = plugin_info( CommandLs )
        assert x['cls'] == CommandLs
        x = plugin_info( ls )
        assert x['cls'] == CommandLs

    def test_interface_info( self ):
        x = interface_info( 'ICommand' )
        assert x['cls'] == ICommand
        x = interface_info( ICommand )
        assert x['cls'] == ICommand

    def test_pluginnames( self ):
        plugins = pluginnames()
        assert 'baseresource' in plugins
        assert 'commandcommands' in plugins
        assert 'commandconfig' in plugins
        assert 'commandls' in plugins
        assert 'commandmounts' in plugins
        assert 'commandserve' in plugins
        assert 'commandunittest' in plugins
        assert 'httprequest' in plugins
        assert 'httpresponse' in plugins
        assert 'plugin' in plugins
        assert 'rootapp' in plugins
        assert 'webapp' in plugins

        plugins = pluginnames( ICommand )
        assert 'commandcommands' in plugins
        assert 'commandconfig' in plugins
        assert 'commandls' in plugins
        assert 'commandmounts' in plugins
        assert 'commandserve' in plugins
        assert 'commandunittest' in plugins
        assert 'webapp' not in plugins

    def test_pluginclass( self ):
        from pluggdapps.commands.ls import CommandLs
        assert pluginclass( ICommand, 'commandls' ) == CommandLs

    def test_whichmodule( self ):
        assert whichmodule(UnitTest_Plugin).__name__ == 'pluggdapps.plugin'
        assert whichmodule(self).__name__ == 'pluggdapps.plugin'
        assert whichmodule(whichmodule).__name__ == 'pluggdapps.plugin'


if __name__ == '__main__' :
    unittest.main()
