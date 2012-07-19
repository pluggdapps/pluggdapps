# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import logging

from   pluggdapps.const         import ROOTAPP
from   pluggdapps.config        import ConfigDict
from   pluggdapps.core          import implements, pluginname
from   pluggdapps.plugin        import Plugin, query_plugins
from   pluggdapps.interfaces    import ICommand
import pluggdapps.utils         as h

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

    def subparser( self, parser, subparsers ):
        name = pluginname( self )
        self.subparser = subparsers.add_parser( 
                                name, description=self.description )
        self.subparser.set_defaults( handler=self.handle )

    def handle( self, args ):
        commands = query_plugins( ROOTAPP, ICommand )
        commands = sorted( commands, key=lambda x : pluginname(x) )
        for command in commands :
            rows = self._formatdescr(pluginname(command), command.description)
            for r in rows : print(r)

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
                line = ' '.join([ x for x in [line,word] if x ])
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
