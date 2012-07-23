# -*- coding: utf-8 -*-

import os, errno 
from   struct               import pack, unpack

from   pluggdapps.erlcodec  import *

# TODO : 
#   * Before packing Convert `data` to binary. So that 
#       { Port, {data, Data} } is received as binary as well.
#   * Unit testing for compressed marshalling is yet to be completed.

__all__ = [ 'Port' ]

formats = { 1: "B", 2: ">H", 4: ">I" }

class Port( object ):

    def __init__( self, descrs=True, packet=4, compressed=False ):
        self._format = formats.get( packet, None )
        if self._format is None :
            raise Exception("Invalid packet size %r" % packet)
        self.packet = packet
        self.compressed = compressed
        self.ind, self.outd = descrs

    def _read_data( self, length ):
        data = b""
        while length > 0:
            try:
                buf = os.read( self.ind, length )
            except OSError as err :
                if err.errno == errno.EPIPE : 
                    raise EOFError( "End of read pipe" )
                raise
            if not buf:
                raise EOFError( "read_data buffer empty" )
            data += buf
            length -= len(buf)
        return data

    def _read( self ):
        data = self._read_data( self.packet )
        length = unpack( self._format, data )[0]
        data = self._read_data( length )
        return decode( data )

    def _write( self, message ):
        data = encode( message, compressed=self.compressed )
        # TODO : Before packing Convert `data` to binary. So that 
        # { Port, {data, Data} } is received as binary as well.
        data = pack( self._format, len(data) ) + data
        while len(data) != 0:
            try:
                n = os.write(self.outd, data)
            except IOError as err:
                if err.errno == errno.EPIPE : 
                    raise EOFError( "End of write pipe" )
                raise
            if n == 0 :
                raise EOFError( "Unable to write to port" )
            data = data[n:]

    def listen( self ):
        if self.ind :
            message = self._read()
            if message[0] != ATOM_REQ :
                raise Exception( "Received a non request %r" % message[0] )
            return message[1:]

    def respond( self, resp ):
        if self.outd != None :
            self._write( (ATOM_RESP, resp) )

    def request( self, method, *args, **kwargs ):
        self._write( (ATOM_REQ, method, list(args), kwargs) )
        message = self._read()
        if message[0] != ATOM_RESP :
            raise Exception( "Expected a response %r" % message[0] )
        return message[1]

    def post( self, method, *args, **kwargs ):
        self._write( (ATOM_POST, method, list(args), kwargs) )

    def logerror( self, formatstr, values ):
        self.post( ATOM_LOGERROR, formatstr, values )

    def loginfo( self, formatstr, values ):
        self.post( ATOM_LOGINFO, formatstr, values )

    def logwarning( self, formatstr, values ):
        self.post( ATOM_LOGWARN, formatstr, values )

    def close(self):
        os.close(self.ind)
        os.close(self.outd)
        self.ind, self.outd = (None, None)
