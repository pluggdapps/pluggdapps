# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

from   pluggdapps.plugin     import implements, Singleton
from   pluggdapps.interfaces import ICommand
import pluggdapps.utils as h


class PViews( Singleton ):
    """Pluggdapps can host many application, and application instances, in the
    same environment and each application can have any number of view-callables
    mapped onto url-paths. Use this sub-command, ``pviews``, to print a summary
    of matching routes and views for a given URL-path
    
    Note that the main script must be invoked using `webapps` platform, the
    ``-w`` switch.


    .. code-block:: text
        :linenos:

        $ pa -w pviews <url-path>

        mountat = <netpath>
        urlpath = <url-path>

            ...
            view-details
            ....

        mountat = <netpath>
        urlpath = <url-path>

            ...
            view-details
            ....

    Typically, for the same application instance, there can be many views mapped
    to same url-path, but differentiated by HTTP request methods and/or
    modifiers. If that is the case you will be getting more than one list for
    the same url-path.

    **netpath** tells the url-prefix (subdomain / host / script-path) on which
    the application is mounted. By default, if no other sub-command option is
    specified, matching views will be listed for all mounted application
    including every instance of the same application. This is useful when each
    application instance has its router configuration different from one
    another.

    There are couple of options that can filter or expand the view listing
    based on netpath.

    - **-a** option takes a plugin-name and lists matching views for all
      instance of application specified by the plugin-name.
    - **-n** option takes a netpath and lists matching views for
      application instance mounted onto that netpath.

    Each view listing might include following information,

    * route-name, route-pattern, route-path, route-predicates.
    * view-callable, view-predicates. View-predicates shall include
      authorisation and authentication.

    """

    implements( ICommand )

    description = "List matching views for url-path"
    cmd = 'pviews'

    #---- ICommand API methods

    def subparser( self, parser, subparsers ):
        """:meth:`pluggdapps.interfaces.ICommand.subparser` interface
        method."""
        self.subparser = subparsers.add_parser( 
                                self.cmd, description=self.description )
        self.subparser.set_defaults( handler=self.handle )
        self.subparser.add_argument(
            "-n", dest="netpath",
            default=None,
            help="List view for application mounted on <netpath>" )
        self.subparser.add_argument(
            "-a", dest="appname",
            default=None,
            help="List view for all instance of application <appname>" )
        return parser

    def handle( self, args ):
        """:meth:`pluggdapps.interfaces.ICommand.handle` interface method."""
        print( 'hello world' )

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        """:meth:`pluggdapps.plugin.ISettings.default_settings` interface 
        method."""
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        """:meth:`pluggdapps.plugin.ISettings.normalize_settings` interface 
        method."""
        return sett


_default_settings = h.ConfigDict()
_default_settings.__doc__ = PViews.__doc__

