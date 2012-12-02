# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

from   pluggdapps.plugin        import implements, Singleton, pluginname
from   pluggdapps.interfaces    import ICommand
import pluggdapps.utils         as h

_default_settings = h.ConfigDict()
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

class CommandCommands( Singleton ):
    """Subcommand plugin under pa-script to list all available sub-commands 
    along with a short description."""

    implements( ICommand )

    description = 'list of script commands and their short description.'
    cmd = 'commands'

    #---- ICommand API
    def subparser( self, parser, subparsers ):
        """:meth:`pluggdapps.interfaces.ICommand.subparser` interface method."""
        self.subparser = subparsers.add_parser( 
                                self.cmd, description=self.description )
        self.subparser.set_defaults( handler=self.handle )

    def handle( self, args ):
        """:meth:`pluggdapps.interfaces.ICommand.handle` interface method."""
        commands = self.query_plugins( ICommand )
        commands = sorted( commands, key=lambda x : pluginname(x)[7:] )
        for command in commands :
            rows = self._formatdescr( pluginname(command)[7:],
                                      command.description )
            for r in rows : print(r)

    #---- Internal & local functions
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
        """:meth:`pluggdapps.plugin.ISettings.default_settings` interface 
        method."""
        return _default_settings

    @classmethod
    def normalize_settings( cls, settings ):
        """:meth:`pluggdapps.plugin.ISettings.normalize_settings` interface 
        method."""
        settings['description_width'] = h.asint(settings['description_width'])
        settings['command_width'] = h.asint(settings['command_width'])
        return settings
