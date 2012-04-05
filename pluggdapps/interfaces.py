# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from plugincore     import Interface, Attribute

__all__ = [ 'ICommand' ]

class ICommand( Interface ):
    """Handle sub-commands issued from command line script. The general
    purpose is to parse the command line string arguments into `options` and
    `arguments` and then perform the sub-command in the user desired 
    fashion."""

    def __init__( argv=[], settings={} ):
        """Parse command line arguments using argv list and return a tuple of
        (options, args).
        """

    def argparse( argv ):
        """Parse command line arguments using argv list and return a tuple of
        (options, args). Also overwrite self's `options` and `args` attributes
        initialized during instantiation.
        """

    def run( options=None, args=[] ):
        """Run the command using command line `options` and non-option 
        parameters, `args`. If either or both `options` and `args` are None 
        then previously parsed `options` and `args` using argparse() will be
        used."""


class ISettings( Interface ):
    """ISettings is a mixin interface that can be implemented of any plugin.
    Especially plugins that support configuration. Note that a plugin is a
    bunch of configuration parameters implementing one or more interface
    specification.
    """

    def normalize_settings( settings ):
        """`settings` is a dictionary of configuration parameters. This method 
        will be called after aggregating all configuration parameters for a
        plugin and before updating the plugin instance with its configuration
        parameters.

        Use this method to do any post processing on plugin's configuration
        parameter and return the final form of configuration parameters."""

    def default_settings( settings ):
        """Return instance of :class:`ConfigDict` providing meta data
        associated with each configuration parameters supported by the plugin.
        Like - default value, value type, help text, wether web configuration
        is allowed, optional values, etc ...
        
        To be implemented by classed deriving :class:`Plugin`.
        """

    def web_admin( settings ):
        """Plugin settings can be configured via web interfaces and stored in
        a backend like database, files etc ... Use this method for the
        following,
        
        * To update the in-memory configuration settings with new `settings`
        * To persist new `settings` in a backend data-store."""


class IConfig( Interface ):
    """Convert configuration parameters from source format, like ini, json,
    database, to dictionary of plugin settings."""

    def settings( spec ):
        """`spec` is a dictionary of information to parse configuration
        parameter into settings map.

        Return a map from plugin names to plugin settings. A special
        plugin-name `DEFAULT` is interpreted as global settings applicable to
        all plugins."""


class IApplication( Interface ):
    """In pluggdapps, an application is a plugin, whereby, a plugin is a bunch
    of configuration parameters implementing one or more interface
    specification."""

    def boot( inifile ):
        """Every application boots from an inifile which is a one time
        activity. Configuration settings from this inifile overrides
        application package's default settings. The implementer of this method
        can also can be
        settings from the original inifile can be overriden using settings derived from """

    def start( request ):

    def finish( request ):

    def router( request ):


class IRouter( Interface ):

    def route( request ):

    def match( request ):
