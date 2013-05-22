# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import io

from   pluggdapps.plugin        import implements, Singleton
from   pluggdapps.interfaces    import ICommand
import pluggdapps.utils         as h

class ConfDoc( Singleton ):
    """Subcommand plugin for pa-script to generate configuration document
    from :meth:`pluggdapps.plugin.ISettings.default_settings` method.
    
    .. code-block:: bash
        :linenos:
        
        $ pa confdoc

    Configuration document can be generated for plugins under a particular
    package. Generated document is in .rst format.
    """

    implements( ICommand )

    description = 'Generate catalog of configuration for plugins.'
    cmd = 'confdoc'

    #---- ICommand API
    def subparser( self, parser, subparsers ):
        """:meth:`pluggdapps.interfaces.ICommand.subparser` interface method.
        """
        self.subparser = subparsers.add_parser( 
                                self.cmd, description=self.description )
        self.subparser.set_defaults( handler=self.handle )
        self.subparser.add_argument(
                "-p", dest="package",
                default='',
                help="package name. Restrict plugins under the package." )
        self.subparser.add_argument(
                "-o", dest="outpath",
                default=None,
                help="Output file name for generated document." )
        return parser

    def handle( self, args ):
        """:meth:`pluggdapps.interfaces.ICommand.handle` interface method."""
        from pluggdapps.plugin import PluginMeta
        catalog = ""
        package = (args.package + ':') if args.package else ''
        catalogf = args.outpath or 'configuration.rst'

        for name, info in sorted( PluginMeta._pluginmap.items() ) :
            if info['assetspec'].startswith( package ) :
                catalog += name + '\n' + (len(name) * '-') + '\n\n'
                catalog += h.conf_catalog( name )
                catalog += '\n'
        open( catalogf, 'w' ).write( catalog )

    # ISettings interface methods
    @classmethod
    def default_settings( cls ):
        """:meth:`pluggdapps.plugin.ISettings.default_settings` interface 
        method."""
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        """:meth:`pluggdapps.plugin.ISettings.normalize_settings` interface 
        method."""
        return settings


_default_settings = h.ConfigDict()
_default_settings.__doc__ = ConfDoc.__doc__

