import os, sys, errno, traceback
from   struct       import pack, unpack
from   erlterms     import Atom, encode, decode


def run( port ):
    """Read loop, read and handle commands, until the port is closed."""
    while True :
        try:
            message = port.read()
            port.write( apply( message ))
        except EOFError:
            break


def pyapply( message ):
    """All messages are function calls of the form,

        ( func_name, [arg1, ... ], [(key1, value1), ...] )

    Apply them and send back the result.
    """
    if not isinstance(message, tuple) :
        response = Atom( "Message is expected as a tuple" )
    else :
        name, args, kwargs = message
        kwargs = dict( kwargs )
        func = globals()[ name ]
        if callable( func ) :
            response = func( *args, **kwargs )
        else :
            response = Atom( "%r is not a callable" % name )
    return response


def erapply( mod, func, args ):
    """Make a function call to erlang world in MFA form"""
    pass


formats = { 1: "B", 2: ">H", 4: ">I" }

class Port( object ):

    def __init__( self, packet=1, use_stdio=False, compressed=None ):
        self._format = formats.get( packet, None )
        if self._format is None :
            raise "Invalid packet size %r" % packet
        self.packet = packet
        self.compressed = compressed
        self.ind, self.outd = 0, 1

    def read_data( self, length ):
        data = ""
        while length > 0:
            try:
                buf = os.read(self.ind, length)
            except OSError, reason:
                if reason.errno == errno.EPIPE : raise EOFError()
                raise
            if not buf:
                raise EOFError()
            data += buf
            length -= len(buf)
        return data

    def read( self ):
        data = self.read_data( self.packet )
        length = unpack( self._format, data )[0]
        data = self.read_data( length )
        return decode( data )[0]

    def write( self, message ):
        data = encode( message, compressed=self.compressed )
        data = pack( self._format, len(data) ) + data
        while len(data) != 0:
            try:
                n = os.write(self.outd, data)
            except IOError, why:
                if why.errno == errno.EPIPE : raise EOFError()
                raise
            if n == 0 :
                raise EOFError()
            data = data[n:]

    def close(self):
        os.close(self.ind)
        os.close(self.outd)
