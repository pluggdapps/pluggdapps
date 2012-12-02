#! /usr/bin/env python3.2

# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""
Executable for netscale cloud platform to dispatch pluggdapps plugin requests.
Pluggdapps instance is launched by executing this command.

* Sets up virtual environment.
* Boots Pluggdapps platform using command line arguments supplied by netscale.
* Loops on IO pipe communicating with netscale platform, marshalling and
  de-marshalling erlang terms, interpreting them.

Notes :
    Request from erlang
      { req, Method, [Arg], [KWArg] }
    Response back to erlang
      { resp, Response }
    Response can be,
        {ok, Result}
      | {error, Reason}

    Request from Python
      { req, Method,[Arg], [KWArg] }
      { post, Method,[Arg], [KWArg] }
    Response back to erlang
      { resp, Response }
"""

import os, sys, traceback, argparse, site, time
from   os.path  import dirname, join, abspath

def run( erlport ):
    """Read loop, read and handle request methods, until the port is closed."""
    while True :
        try:
            request = erlport.listen()
            if isinstance( request, tuple ) :
                resp = handle( erlport, request )
            else :
                resp = ( ATOM_ERROR, "request expected as tuple" )
            erlport.respond( resp )
        except EOFError:
            break
        except Exception as err :
            erlport.logerror( traceback.format_exc(), [] )
            break


def handle( erlport, request ):
    """Handle request from Erlang. Unlike the request made from pluggdapps,
    this is asynchronous."""
    method, args, kwargs = request
    handler = handlerd.get( method, handle_fail )
    result = handler( erlport, method, *args, **dict(kwargs) )
    return (ATOM_OK, result)


#---- Method handlers

def handle_fail( erlport, method, *args, **kwargs ):
    """If a request is received with invalid method, raise exception."""
    raise Exception( "Invalid method %r" % method )


def handle_exit_port( erlport, method, *args, **kwargs ):
    """Erlang has requested a normal exit. This should send message,
        {Port, {exit_status, Status}}
    to the connected process.
    """
    erlport.shutdown()
    sys.exit(0) # Thats it, end of life for this port !!


def handle_close_fds( erlport, method, *args, **kwargs ):
    """Erlang has requested to close the in/out ports. This should send the
    message,
        {Port, eof}
    to the connected process.
    """
    erlport.close()
    return ATOM_OK  


def handle_loopback( erlport, method, *args, **kwargs ):
    """Loopback request. Send back `args` and `kwargs` a tuple. Primarily used
    for Erlang to Python validation"""
    return ( list(args), kwargs )


def handle_reverseback( erlport, method, *args, **kwargs ):
    """Reverseback request. Similar to loopback except that is in the reverse
    order (i.e) from loopback from python to erlang. Primarily used for Erlang
    to Python validation"""
    ref = test_data()
    refstr = "hello world"
    tup = erlport.request( ATOM_LOOPBACK, ref, refstr )
    for x, y in zip(tup[0][0], ref) :
        if x != y : erlport.logerror( "Failed matching ~p ~p ~n", [x, y] )
    if tup[0][1] != refstr :
        erlport.logerror( "Failed matching ~p ~n", [refstr, tup[0][1]] )

    if tup[0] == [ref, refstr] :
        return ATOM_OK
    else :
        return (ATOM_ERROR, tup[0])


def handle_profileback( erlport, method, *args, **kwargs ):
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
        [ erlport.request( Atom('loopback'), tup[1] )
            for x in list(range(tup[2])) ]
        t = time.time() - snow
        erlport.loginfo( "Time take to loop back ~p is ~p Sec ~n", 
                      [Atom(tup[0]), t/tup[2]] )
    return ATOM_OK


def handle_apply( erlport, method, func, *args, **kwargs ):
    """Apply `args` and `kwargs` on function `func`."""
    func = globals().get( func, None )
    if callable( func ) :
        return func( erlport, *args, **kwargs )
    else :
        return (ATOM_ERROR, "%r is not a callable" % func)


def handle_query_plugin( erlport, method, *args, **kwargs ):
    pass

def handle_plugin_attribute( erlport, method, *args, **kwargs ):
    pass

def handle_plugin_method( erlport, method, *args, **kwargs ):
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

#---- Applied methods,

def loadconfig( erlport, *args, **kwargs ):
    pass


def bootapps( erlport, *args, **kwargs ) :
    return (ATOM_OK, erlport.bootapps())


#---- Test case data for reverseback and profileback.

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


#---- Command line 

def pa_dir() :
    """Return pluggdapps package directory."""
    return abspath( dirname( dirname( __file__ )))

def virtualenv( args ):
    """Netscale cloud can be launched with settings for pluggdapps' virtual
    environment. Virtual environment configuration can be absolute or
    relative. If relative, it is assumed to be relative to pa_dir().
    """
    virtenv = args.virtenv
    virtenv = virtenv.replace('/', os.sep) if os.sep != '/' else virtenv
    return [virtenv] if virtenv[0] == os.sep else [ join(pa_dir(), virtenv) ]


def optionparse() :
    parser = argparse.ArgumentParser( description='Erlang port for pluggdapps' )

    parser.add_argument( '--config-ini', dest='configini',
                         default="",
                         help='Absolute location of ini configuration file' )

    parser.add_argument( '--use_stdio', dest='use_stdio',
                         action='store_true', default=False,
                         help='Use standard io 0 & 1 for port communication' )

    parser.add_argument( '--nouse_stdio', dest='nouse_stdio', 
                         action='store_true', default=False,
                         help='Use file descr. 3 & 4 for port communication' )

    parser.add_argument( '--use_descrs', dest='use_descrs', 
                         default='',
                         help='Use CSV of descriptors for port communication' )

    parser.add_argument( '--packet', dest='packet',
                         default='4',
                         help='Message packet size' )

    parser.add_argument( '--virtenv', dest='virtenv',
                         default='pa-env/lib/python3.2/site-packages',
                         help='Virtual python environment for pluggdapps' )

    parser.add_argument( '--compressed', dest='compressed',
                         action='store_true', default=False,
                         help='Use compressed erlang terms' )

    return parser.parse_args()


if __name__ == '__main__' :
    args = optionparse()

    # Setup virtual environment
    papaths = virtualenv( args )
    prev_sys_path = list( sys.path ) # Remember previous path
    site.addsitedir( papaths[0] )    # Add each new site-packages directory.

    # Reorder sys.path so new directories at the front.
    new_sys_path = []
    for item in list( sys.path ) :
        if item not in prev_sys_path:
            new_sys_path.append( item )
            sys.path.remove( item )
    sys.path[:0] = new_sys_path

    # Avoid ``[Errno 13] Permission denied: '/var/www/.python-eggs'`` messages
    os.environ['PYTHON_EGG_CACHE'] = join( pa_dir(), 'egg-cache' )

    # IMPORTANT : pluggdapps package can be imported only at this stage, after
    # setting up the virtual environment.
    import pluggdapps
    from   pluggdapps.erlcodec import *
    from   pluggdapps.const import *
    from   pluggdapps.platform import Pluggdapps

    args.configini = args.configini or DEFAULT_INI

    if args.use_descrs :
        descrs = tuple( map( int, args.use_descrs.split(',') ))
    elif args.nouse_stdio :
        descrs = (3,4)
    else : 
        descrs = (0,1)

    erlport = Pluggdapps.boot( args.configini,
                               # Initializers for Pluggdapps() class
                               erlang=True,
                               # Initializers for Port() class.
                               descrs=descrs,
                               packet=int(args.packet), 
                               compressed=args.compressed )
    run( erlport )

