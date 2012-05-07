# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

from   optparse                 import OptionParser
import sys

from   pluggdapps.plugin        import PluginMeta, Plugin, implements
from   pluggdapps.interfaces    import ICommand


class Info( Plugin ):
    implements( ICommand )

    description = "Platform's environment Information"
    usage = "usage: pa [options] info"

    def __init__( self, platform, argv=[] ):
        self.platform = platform
        parser = self._parse( Info.usage )
        self.options, self.args = parser.parse_args( argv )

    def argparse( self, argv ):
        parser = self._parse( Info.usage )
        self.options, self.args = parser.parse_args( argv )
        return self.options, self.args

    def run( self, options=None, args=[] ):
        options = options or self.options
        args = args or self.args

    def _parse( self, usage ):
        return self._options( OptionParser( usage=usage ))

    def _options( self, parser ):
        return parser
