# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import socket

from pluggdapps.plugin import Interface, Attribute

__all__ = [ 'ICommand', 'IServer' ]

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



class IServer( Interface ):
    """Interface to bind, listen, accept HTTP connections. This interface is
    still evolving."""

    def __init__( *args, **kwargs ):
        """Initialize server."""

    def listen( port, address="" ):
        """Starts accepting connections on the given port and address.
        This method may be called more than once to listen on multiple ports.
        `listen` takes effect immediately;
        """

    def bind( port, address=None, family=socket.AF_UNSPEC, backlog=128 ):
        """Binds this server to the given port on the given address.

        To start the server, call `start`. If you want to run this server
        in a single process, you can call `listen` as a shortcut to the
        sequence of `bind` and `start` calls.

        Address may be either an IP address or hostname.  If it's a hostname,
        the server will listen on all IP addresses associated with the
        name.  Address may be an empty string or None to listen on all
        available interfaces.  Family may be set to either ``socket.AF_INET``
        or ``socket.AF_INET6`` to restrict to ipv4 or ipv6 addresses, otherwise
        both will be used if available.

        The ``backlog`` argument has the same meaning as for
        `socket.listen`.

        This method may be called multiple times prior to `start` to listen
        on multiple ports or interfaces.
        """

    def start( *args, **kwargs ):
        """Starts this server and returns a server object."""

    def stop():
        """Stops listening for new connections.

        Requests currently in progress may still continue after the
        server is stopped.
        """

    def handle_stream( stream, address ):
        """To handle a new connection stream."""


