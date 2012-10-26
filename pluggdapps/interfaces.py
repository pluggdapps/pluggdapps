# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import socket

from pluggdapps.plugin import Interface, Attribute

__all__ = [ 'ICommand' ]

class ICommand( Interface ):
    """Handle sub-commands issued from command line script. The general
    purpose is to parse the command line string arguments into `options` and
    `arguments` and handle sub-commands as pluggable functions."""

    description = Attribute( "Text to display before the argument help." )
    usage = Attribute( "String describing the program usage" )
    cmd = Attribute( "Name of the command" )

    def subparser( parser, subparsers ):
        """Use ``subparsers`` to create a sub-command parser. The `subparsers`
        object would have been created using ArgumentParser object ``parser``.
        """

    def handle( args ):
        """While :meth:`subparser` is invoked, the sub-command plugin can 
        use set_default() method on subparser to set `handler` attribute to
        this method.

        So that this handler will automatically be invoked if the sub-command
        is used on the command line."""



