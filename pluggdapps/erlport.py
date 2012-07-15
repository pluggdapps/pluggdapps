import os, sys, errno, traceback, argparse

from   struct       import pack, unpack
from   erlterms     import Atom, encode, decode

# Request to pa
#   { req, Method, [Arg], [KWarg] }
#
# Response back to pa
#   { resp, Response }

# Methods can be one of the following,
handlerd = {
    'loopback'          : handle_loopback,
    'reverseback'       : handle_reverseback,
    'apply'             : handle_apply,
    'query_plugin'      : handle_query_plugin,
    'plugin_attribute'  : handle_plugin_attribute,
    'plugin_method'     : handle_plugin_method,
}

# Response can be,
#     {ok, Result}
#   | {error, Reason}


def run( port ):
    """Read loop, read and handle methods, until the port is closed."""
    while True :
        try:
            request = port.listen()
            if isinstance( request, tuple ) :
                resp = handle( port, request )
            else :
                resp = ( Atom('error') "request expected as tuple" )
            port.respond( resp )
        except Exception, why :
            try :
                port.response( (Atom('error'), why) )
            except EOFError:
                break
        except EOFError:
            break

def handle( port, request ):
    method, args, kwargs = request
    try :
        result = handlerd.get(method, handlefail)(port, *args, **dict(kwargs))
        return ( Atom('ok'), result )
    except Exception, why :
        return ( Atom('error'), why )

def handlefail( port, method, *args, **kwargs ):
    raise "Invalid message %r" % method

def handle_loopback( port, method, *args, **kwargs ):
    return {args, kwargs}

def handle_reverseback( port, method, *args, **kwargs ):
    fails = []
    for method, args, kwargs in test_reverseback :
        resp = port.request( (method, args, kwargs) )
        fails.append( (method, args, kwargs), resp )
    return fails

def handle_apply( port, method, func, *args, **kwargs ):
    func = globals()[ name ]
    if callable( func ) :
        return func(*args, **kwargs)
    else :
        raise "%r is not a callable" % func

def handle_query_plugin( port, method, *args, **kwargs ):
    pass

def handle_plugin_attribute( port, method, *args, **kwargs ):
    pass

def handle_plugin_method( port, method, *args, **kwargs ):
    pass


formats = { 1: "B", 2: ">H", 4: ">I" }

class Port( object ):

    def __init__( self, packet=4, compressed=False ):
        self._format = formats.get( packet, None )
        if self._format is None :
            raise "Invalid packet size %r" % packet
        self.packet = packet
        self.compressed = compressed
        self.ind, self.outd = 0, 1

    def _read_data( self, length ):
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

    def _read( self ):
        data = self._read_data( self.packet )
        length = unpack( self._format, data )[0]
        data = self._read_data( length )
        return decode( data )[0]

    def _write( self, message ):
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

    def listen( self ):
        message = self._read()
        if message[0] != 'req' :
            raise "Received a non request %r" % message[0]
        return message[1:]

    def respond( self, resp ):
        self._write( (Atom('resp'), resp) )

    def request( self, method, *args, **kwargs ):
        self._write( (Atom('req'), (method, args, kwargs)) )
        message = self._read()
        if message[0] != 'resp' :
            raise "Expected a response %r" % message[0]
        return message[1:]

    def close(self):
        os.close(self.ind)
        os.close(self.outd)


def optionparse() :
    parser = argparse.ArgumentParser( description='Erlang port for pluggdapps' )
    parser.add_argument( '--packet', dest='packet',
                         default='4',
                         help='Message packet size' )
    parser.add_argument( '--compressed', dest='compressed',
                         action='store_true', default=False,
                         help='Message packet size' )
    return parser.parse_args()


if __name__ == '__main__' :
    args = optionparse()
    port = Port( packet=args.packet, compressed=args.compressed )
    run( port )
