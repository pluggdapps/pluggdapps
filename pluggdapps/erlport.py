#! /usr/bin/env python3.2

import os, sys, errno, traceback, argparse, site, time
from   struct   import pack, unpack
from   os.path  import dirname, join, abspath

# TODO : 
#   * Before packing Convert `data` to binary. So that 
#       { Port, {data, Data} } is received as binary as well.

# Notes :
#     Request from erlang
#       { req, Method, [Arg], [KWArg] }
#     Response back to erlang
#       { resp, Response }
#     Response can be,
#         {ok, Result}
#       | {error, Reason}
#
#     Request from Python
#       { req, Method,[Arg], [KWArg] }
#       { post, Method,[Arg], [KWArg] }
#     Response back to erlang
#       { resp, Response }

def run( port ):
    """Read loop, read and handle request methods, until the port is 
    closed."""
    while True :
        try:
            request = port.listen()
            if isinstance( request, tuple ) :
                resp = handle( port, request )
            else :
                resp = ( ATOM_ERROR, "request expected as tuple" )
            port.respond( resp )
        except EOFError:
            print( "Python : Exiting !" )
            break
        except Exception as err :
            raise
            try :
                port.respond( (ATOM_ERROR, err.args[0]) )
            except EOFError:
                print( "Python : Nested exception, Exiting !")
                break


def handle( port, request ):
    """Handle request from Erlang. Unlike the request made from pluggdapps,
    this is asynchronous."""
    method, args, kwargs = request
    try :
        handler = handlerd.get( method, handle_fail )
        result = handler( port, method, *args, **dict(kwargs) )
        return ( ATOM_OK, result )
    except Exception as err :
        raise
        return ( ATOM_ERROR, err.args[0] )


def handle_fail( port, method, *args, **kwargs ):
    """If a request is received with invalid method, raise exception."""
    raise Exception( "Invalid method %r" % method )


def handle_exit_port( port, method, *args, **kwargs ):
    """Erlang has requested a normal exit. This should send message,
        {Port, {exit_status, Status}}
    to the connected process.
    """
    sys.exit(0) # Thats it, end of life for this port !!


def handle_close_fds( port, method, *args, **kwargs ):
    """Erlang has requested to close the in/out ports. This should send the
    message,
        {Port, eof}
    to the connected process.
    """
    port.close()
    return ATOM_OK  


def handle_loopback( port, method, *args, **kwargs ):
    """Loopback request. Send back `args` and `kwargs` a tuple. Primarily used
    for Erlang to Python validation"""
    return ( list(args), kwargs )


def handle_reverseback( port, method, *args, **kwargs ):
    """Reverseback request. Similar to loopback except that is in the reverse
    order (i.e) from loopback from python to erlang. Primarily used for Erlang
    to Python validation"""
    ref = test_data()
    refstr = "hello world"
    tup = port.request( ATOM_LOOPBACK, ref, refstr )
    for x, y in zip(tup[0][0], ref) :
        if x != y : port.logerror( "Failed matching ~p ~p ~n", [x, y] )
    if tup[0][1] != refstr :
        port.logerror( "Failed matching ~p ~n", [refstr, tup[0][1]] )

    if tup[0] == [ref, refstr] :
        return ATOM_OK
    else :
        return (ATOM_ERROR, tup[0])


def handle_profileback( port, method, *args, **kwargs ):
    Int  = ('smallint', 10, 10000)
    BInt = ('bigint', 100000, 10000)
    LInt = ('largeint',
            10000000000000000000000000000000000000000000000000000000000000000 *
            10000000000000000000000000000000000000000000000000000000000000000 *
            10000000000000000000000000000000000000000000000000000000000000000 *
            10000000000000000000000000000000000000000000000000000000000000000 *
            10000000000000000000000000000000000000000000000000000000000000000,
            10000)
    Float = ('float', 10.2, 10000)
    BitS  = ('bitstring', BitString(b'\x01\x02\x03\x55', 3), 10000)
    Atm   = ('atom', Atom('asdfkj123 !@#!@#'), 10000)
    Tuple = ('tuple', (Int, LInt, BInt, Float, BitS, Atm), 10000)
    LTuple = ('largetuple', 100 * Tuple, 100)
    List  = ('list', [Int, LInt, BInt, Float, BitS, Atm ], 10000)
    Bin   = ('binary', b'hello world'*500, 10000)
    LBin  = ('largebinary', b'hello world'*500000, 10)
    Data  = ('data', test_data(),100)

    for tup in [ Int, BInt,LInt, Float, BitS, Atm, Tuple, LTuple,
                 List, Bin, LBin, Data] :
        snow = time.time()
        [ port.request( Atom('loopback'), tup[1]) for x in list(range(tup[2])) ]
        t = time.time() - snow
        port.loginfo( "Time take to loop back ~p is ~p Sec ~n", 
                      [Atom(tup[0]), t/tup[2]] )

def handle_apply( port, method, func, *args, **kwargs ):
    func = globals()[ name ]
    if callable( func ) :
        return func(*args, **kwargs)
    else :
        raise Exception( "%r is not a callable" % func )

def handle_query_plugin( port, method, *args, **kwargs ):
    pass

def handle_plugin_attribute( port, method, *args, **kwargs ):
    pass

def handle_plugin_method( port, method, *args, **kwargs ):
    pass


# Methods can be one of the following,
handlerd = {
    # Methods allowed only from Erlang to Python
    'exit_port'         : handle_exit_port,
    'close_io'          : handle_close_fds,
    'reverseback'       : handle_reverseback,
    'profileback'       : handle_profileback,
    # Methods allowed only from Python to Erlang
    'logerror'          : None,
    'loginfo'           : None,
    'logwarn'           : None,
    # Methods allowed both ways
    'loopback'          : handle_loopback,
    'apply'             : handle_apply,
    'query_plugin'      : handle_query_plugin,
    'plugin_attribute'  : handle_plugin_attribute,
    'plugin_method'     : handle_plugin_method,
}


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

#---- Local test cases
def test_data() :
    tup = ( 10.2, 10000000000000.2, 0.00000000001, 
            BitString(b'\x60\x05', 3),
            BitString(b'\x01\x02\x03\x05', 3),
            10, 1000000, 1000000000000000000000000000000000000000,
            Atom('hello'), Atom('dasfdksfaj!@#!@#!@'),
            tuple( list(range(1, 1000 ))),
            [],
            "hello world",
            list(range( 1, 1000 )),
            b'\x01\x02\x03\x04\x05',
          )
    return [ 10.2, 10000000000000.2, 0.00000000001, 
             BitString(b'\x77',4), BitString(b'\x01\x02\x03\x55', 6),
             10, 1000000, 1000000000000000000000000000000000000000,
             Atom('hello'), Atom('dasfdksfaj!@#!@#!@'), tup, 
             b'\x01\x02\x03\x04\x05', list(range(1, 1000)) ]
#----    


def optionparse() :
    parser = argparse.ArgumentParser( description='Erlang port for pluggdapps' )
    parser.add_argument( '--use_stdio', dest='use_stdio',
                         action='store_true', default=False,
                         help='Use standard io 0 & 1 for port communication' )
    parser.add_argument( '--nouse_stdio', dest='nouse_stdio', 
                         action='store_true', default=False,
                         help='Use file descriptors 3 & 4 for port communication' )
    parser.add_argument( '--use_descrs', dest='use_descrs', 
                         default='',
                         help='Use CSV of descriptors for port communication' )
    parser.add_argument( '--packet', dest='packet',
                         default='4',
                         help='Message packet size' )
    parser.add_argument( '--paenv', dest='paenv',
                         default='pa-env/lib/python3.2/site-packages',
                         help='Virtual python environment for pluggdapps' )
    parser.add_argument( '--compressed', dest='compressed',
                         action='store_true', default=False,
                         help='Message packet size' )
    return parser.parse_args()


def pa_dir() :
    return abspath( dirname( dirname( __file__ )))

def virtualenv( args ):
    paenv = args.paenv.replace('/', os.sep) if os.sep != '/' else args.paenv
    return [ join(pa_dir(), paenv) ]

if __name__ == '__main__' :
    args = optionparse()

    # Setup virtual environment
    papaths = virtualenv( args )
    prev_sys_path = list( sys.path ) # Remember previous path
    site.addsitedir( papaths[0] )  # Add each new site-packages directory.

    # Reorder sys.path so new directories at the front.
    new_sys_path = []
    for item in list( sys.path ) :
        if item not in prev_sys_path:
            new_sys_path.append( item )
            sys.path.remove( item )
    sys.path[:0] = new_sys_path

    # Avoid ``[Errno 13] Permission denied: '/var/www/.python-eggs'`` messages
    os.environ['PYTHON_EGG_CACHE'] = join( pa_dir(), 'egg-cache' )

    from pluggdapps.erlcodec import *

    if args.use_descrs :
        descrs = tuple( map( int, args.use_descrs.split(',') ))
    elif args.nouse_stdio :
        descrs = (3,4)
    else : 
        descrs = (0,1)
    port = Port( descrs=descrs, packet=int(args.packet), 
                 compressed=args.compressed )
    run( port )

