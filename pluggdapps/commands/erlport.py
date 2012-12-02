# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Python side port handler that bridges with erlang's port interface. After
the pluggdapps instance is launched, by executing erlmain.py, this module is
the entry point for all messages from erlang's netscale / OTP system.

**IMPORTANT : This part is under work and shall go through heavy design
changes.**

**data path** ::

    |                  RESPONSE
    |   *----------------------------------*
    |   |                                  |
    |   V       REQUEST                    |
    | netscale ---------> pluggdapps       |
    |    |^                   |            |
    |    ||                   |            |
    |    || REQUEST           V            |
    |    |*--------------- process --------*
    |    *----------->  in pluggdapps
    |       RESPONSE

**Notes**

  * For every pluggdapps port that is spawned using open_port() there will be
    one and only one erlang process that is connected to that port. It is the
    proc's reponsibility to serialize messages to its port.

  * At any given time, there can be only one on-going request to the port.
    Next request is sent only after the connected process recieves a response.

  * While a request is being services by pluggapps port, the port can generate
    any number of request to  netscale. And the connected process on erlang
    side should considered these requests under the context of its original
    request to the port.

REQUEST message:
----------------
  
  **Format : { Method, Args }**

``Method``,
    Denotes the type of request. Methods are explained below.

``Args``,
    List of arguments that are semantically related to `Method`.

``KWargs``,
    Property-list, list of key,value pairs, that are semantically related to
    `Method`.

RESPONSE message:
-----------------

  **Format : { Data } **

Since requests are serialized, any message that does not have an arity of 2
and a valid Method as its first element should be considered as response
tuple. Which contains a single term.

Request method:
---------------

ATOM_GET,

ATOM_POST,

ATOM_LOOPBACK,

ATOM_APPY,

ATOM_QUERY_PLUGIN,

ATOM_PLUGIN_ATTRIBUTE,

ATOM_PLUGIN_METHOD,

"""

import os, errno 
from   struct               import pack, unpack

# TODO : 
#   * Before packing Convert `data` to binary. So that 
#       { Port, {data, Data} } is received as binary as well.
#   * Unit testing for compressed marshalling is yet to be completed.

__all__ = [ 'ErlPort' ]

formats = { 1: "B", 2: ">H", 4: ">I" }

class ErlPort( object ):
    """Port class that handles data marshalling between netscale and
    pluggdapps.

    `descrs`,
        2 arity tuple of IO pipes to use for communicating with netscale
        system.
    `packet`,
        packet protocol configuration. Refer erlang:open_port()
    `compressed`,
        Compression level to use for erlang's binary terms. Specifying 0 or
        False indicates no compression.
    """

    def __init__( self, descrs=(3,4), packet=4, compressed=False ):
        self._format = formats.get( packet, None )
        if self._format is None :
            raise Exception("Invalid packet size %r" % packet)
        self.packet = packet
        self.compressed = compressed
        self.ind, self.outd = descrs

    def _read_data( self, length ):
        """Internal function to read `length` bytes of data from erlang side.
        Return data as bytes."""
        data = b""
        while length > 0:
            buf = os.read( self.ind, length )
            if not buf:
                return b''
            data += buf
            length -= len(buf)
        return data

    def _read( self ):
        """Internal function to read and decode a single binary term from
        erlang side.

        Blocks until an entire erlang term is read and returns python data.
        """
        from pluggdapps.erl.codec import decode
        if self.ind :
            data = self._read_data( self.packet )
            length = unpack( self._format, data )[0]
            data = self._read_data( length )
            return decode( data )
        return None

    def _write( self, val ):
        """Internal function to encode python data `val` to erlang binary term
        and send them to erlang side."""
        from pluggdapps.erl.codec  import encode
        if self.outd :
            # Received at erlang side as { Port, {data, Data} }.
            data = encode( val, compressed=self.compressed )
            data = pack( self._format, len(data) ) + data

            while len(data) != 0:
                n = os.write(self.outd, data)
                if n == 0 : 
                    return None
                data = data[n:]
        return None

    def listen( self ):
        """Blocking call, listening for a REQUEST from erlang-netscale
        side."""
        return self._read()

    def respond( self, resp ):
        """Send response message to erlang-netscale world. All response
        correspond to a request."""
        return self._write( (resp) )

    def request( self, method, *args ):
        """As part of processing a response, pluggdapps can generate
        requests. Waits for the response from erlang."""
        self._write(( method, list(args) ))
        return self._read()

    def post( self, method, *args ):
        """Similar to request() except that it does not expect a response
        back. So return immediately to the caller."""
        self._write(( method, list(args) ))

    def logerror( self, formatstr, values ):
        """Marshall logging to erlang."""
        self.post( ATOM_LOGERROR, formatstr, values )

    def loginfo( self, formatstr, values ):
        """Marshall logging to erlang."""
        self.post( ATOM_LOGINFO, formatstr, values )

    def logwarning( self, formatstr, values ):
        """Marshall logging to erlang."""
        self.post( ATOM_LOGWARN, formatstr, values )

    def close(self):
        """Close the  port. Once close, the only logical next is to shutdown
        the port process."""
        os.close(self.ind)
        os.close(self.outd)
        self.ind, self.outd = (None, None)
