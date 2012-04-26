# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from   optparse                 import OptionParser
import logging

from   pluggdapps.config        import ConfigDict
from   pluggdapps.plugin        import Plugin, implements, query_plugins, \
                                       pluginname
from   pluggdapps.interfaces    import ICommand
import pluggdapps.helper        as h

log = logging.getLogger(__name__)

_default_settings = ConfigDict()
_default_settings.__doc__ = \
    "Configuration settings `commands` plugin."

_default_settings['description_width']  = {
    'default' : 60,
    'types'   : (int,),
    'help'    : "Maximum width of description column."
}
_default_settings['command_width']  = {
    'default' : 18,
    'types'   : (int,),
    'help'    : "Maximum width of command name column."
}

class Commands( Plugin ):
    implements( ICommand )

    description = "list of script commands and their short description."
    usage = "usage: pa [options] commands"

    def __init__( self, platform, argv=[] ):
        self.platform = platform
        parser = self._parse( Commands.usage )
        self.options, self.args = parser.parse_args( argv )

    def argparse( self, argv ):
        parser = self._parse( List.usage )
        self.options, self.args = parser.parse_args( argv )
        return self.options, self.args

    def run( self, options=None, args=[] ):
        from pluggdapps import ROOTAPP
        options = options or self.options
        args = args or self.args
        commands = query_plugins( ROOTAPP, ICommand, self.platform )
        commands = sorted( commands, key=lambda x : pluginname(x) )
        for command in commands :
            rows = self._formatdescr(pluginname(command), command.description)
            for row in rows :
                print row

    def _parse( self, usage ):
        return self._options( OptionParser( usage=usage ))

    def _options( self, parser ):
        return parser

    def _formatdescr( self, name, description ):
        fmtstr = '%-' + str(self['command_width']) + 's %s'
        l = self['description_width']

        rows, line = [], ''
        words = ' '.join( description.strip().splitlines() ).split(' ')
        while words :
            word = words.pop(0)
            if len(line) + len(word) >= l : 
                rows.append( fmtstr % (name, line) )
                line, name = word, ''
            else :
                line = ' '.join(filter(None, [line, word]))
        rows.append( fmtstr % (name, line) ) if line else None
        return rows

    # ISettings interface methods
    @classmethod
    def default_settings( cls ):
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        settings['description_width'] = h.asint(settings['description_width'])
        settings['command_width'] = h.asint(settings['command_width'])
        return settings
