# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Erlang external term format.
    Refer : http://www.erlang.org/doc/apps/erts/erl_ext_dist.html

Python equivalent for erlang term.
    number      - Native number
    float       - Native float
    atom        - Atom() class object
    bool        - Native boolean
    fun         - Not Implemented
    bit-string  - BitString() class object
    binary      - Native bytes
    reference   - Reference() class object
    port        - Port() class object
    pid         - Pid() class object
    tuple       - Native tuple
    list        - Native list
    string      - tuple( Atom('nstr'), <binary> )
    record      - tuple( Atom(), ... )
"""

from   struct     import pack, unpack
from   array      import array
from   zlib       import decompressobj, compress
import builtins

from   pluggdapps.erl.terms import *

# TODO :
#   * Unable to gather type of None.

__all__ = [ 'decode', 'encode' ]

ordnil = ord( "j" )

def assert_true( val, msg=None ) :
    msg = msg or "Assertion failed in marshalling erlang terms"
    if val != True : 
        raise Exception( msg )

#---- APIs

def decode( bstr ):
    """Decode Erlang external term represented in binary."""
    version = bstr[0]   # Expected to be '131'

    if bstr[1:2] == b'\x50' :   # compressed term
        d = decompressobj()
        termbin = d.decompress( bstr[6:] ) + d.flush()
        uncompressed_size = unpack( '>I', bstr[2:6] )[0]
        return decode_term( termbin[:uncompressed_size] )[0]
    else :                      # Un-compressed term
        return decode_term( bstr[1:] )[0]


def encode( term, compressed=False ):
    """Encode python data to erlang term, with optional compression
    settings."""
    encoded_term = encode_term( term )
    # False or 0 do not attempt compression.
    if compressed :
        zlib_term = compress( encoded_term, compressed )
        if len(zlib_term)+5 <= len(encoded_term): # compressed term is smaller
            return b'\x83\x50' + pack('>I', len(encoded_term)) + zlib_term
    return b"\x83" + encoded_term


#---- Decoder

def decode_term( termbin ):
    return decoders.get( termbin[0], invalid_tag )( termbin[1:] )


#-- Decode handler for each erlang term-binary.

def invalid_tag( data ):
    """Handler for invalid tag found in term-binary"""
    raise Exception( "Unsupported erlang term: %i" % tag )


def decode_atom_cacheref( b ):
    """ *----*----------------------------*
        | 1  |  1                         |
        *----*----------------------------*
        | 82 | Atom cache reference index |
        *----*----------------------------* """
    raise Exception( "Atom cache reference erlang term is not supported" )


def decode_smallint( b ):
    """ *----*-----*
        | 1  |  1  |
        *----*-----*
        | 97 | Int |
        *----*-----* """
    return ord(b[0]), b[1:]


def decode_int( b ):
    """ *----*-----*
        | 1  |  4  |
        *----*-----*
        | 98 | Int |
        *----*-----* """
    return unpack( ">i", b[:4] )[0], b[4:]


def decode_float( b ):
    """ *----*--------------*
        | 1  |      31      |
        *----*--------------*
        | 99 | Float String |
        *----*--------------* """
    return float( b[:31].split(b"\x00", 1)[0] ), b[31:]


def decode_atom( b ):
    """ *-----*-----*----------*
        |  1  |  2  |    Len   |
        *-----*-----*----------*
        | 100 | Len | AtomName |
        *-----*-----*----------*

    Note that atom names are binary and right-now encoded in 'latin-1'. In
    future this might change.
    """
    l = unpack( ">H", b[:2] )[0]
    
    return Atom( b[2:l].decode('latin-1') ), b[2+l:]


def decode_reference( b ):
    """ *-----*-----*-----*----------*
        |  1  |  N   |  4 |    1     |
        *-----*-----*-----*----------*
        | 101 | Node | ID | Creation |
        *-----*-----*-----*----------* """
    raise Exception( "Old reference erlang term is not supported" )


def decode_port( b ):
    """ *-----*------*----*----------*
        |  1  |  N   | 4  |    1     |
        *-----*------*----*----------*
        | 102 | Node | ID | Creation |
        *-----*------*----*----------* """
    node, tail = decode_atom(b)
    return Port( node, tail[:4], tail[4] ), tail[5:]


def decode_pid( b ):
    """ *-----*------*----*--------*----------*
        |  1  |  N   | 4  |  4     |    1     |
        *-----*------*----*--------*----------*
        | 103 | Node | ID | serial | Creation |
        *-----*------*----*--------*----------* """
    node, tail = decode_atom(b)
    return Port( node, tail[:4], tail[4:8], tail[8] ), tail[9:]


def decode_smalltuple( b ):
    """ *-----*-------*----------*
        |  1  |  1    |    N     |
        *-----*-------*----------*
        | 104 | Arity | Elements |
        *-----*-------*----------* """
    arity, tail = b[0], b[1:]
    lst = []
    while arity > 0 :
        term, tail = decode_term(tail)
        lst.append(term)
        arity -= 1
    tup = tuple(lst)

    if tup[0] == ATOM_NSTR : # Strings are marshalled as, {nstr, binary}
        return tup[1].decode( 'utf8' ), tail
    else :
        return tup, tail


def decode_largetuple( b ):
    """ *-----*-------*----------*
        |  1  |  4    |    N     |
        *-----*-------*----------*
        | 105 | Arity | Elements |
        *-----*-------*----------* """
    arity, tail = unpack(">I", b[:4])[0], b[4:]
    lst = []
    while arity > 0:
        term, tail = decode_term(tail)
        lst.append(term)
        arity -= 1
    return tuple(lst), tail


def decode_nil( b ):
    """ *-----*
        |  1  |
        *-----*
        | 106 |
        *-----* """
    return [], b


def decode_string( b ):
    """Actually not a string. Erlang's term_to_binary automatically interprets
    lists (containing integers < 255) as string.
        *-----*-------*--------*
        |  1  |  2    |  Len   |
        *-----*-------*--------*
        | 107 | Len   | Chars  |
        *-----*-------*--------*

    Note that `Chars` are expected to be in latin1.
    """
    l = unpack( ">H", b[:2] )[0]
    return b[2:2+l].decode('latin1'), b[2+l:]


def decode_list( b ):
    """ *-----*------*----------*------*
        |  1  |  4   |  Len     |  N   |
        *-----*------*----------*------*
        | 108 | Len  | Elements | Tail |
        *-----*------*----------*------* """
    l, tail = unpack( ">I", b[:4] )[0], b[4:]
    lst = []
    while length > 0:
        term, tail = decode_term(tail)
        lst.append(term)
        length -= 1
    list_tail, tail = decode_term(tail)
    lst.append(  list_tail ) if list_tail else None
    return lst, tail


def decode_binary( b ):
    """ *-----*------*------*
        |  1  |  4   |  Len |
        *-----*------*------*
        | 109 | Len  | Data |
        *-----*------*------* """
    l, tail = unpack( ">I", b[:4] )[0], b[4:]
    return tail[:l], tail[l:]


def decode_smallbig( b ):
    """ *-----*-----*------*------------------------*
        |  1  |  1  |  1   |    Len                 |
        *-----*-----*------*------------------------*
        | 110 | Len | Sign | d[0],d[1],...,d[Len-1] |
        *-----*-----*------*------------------------* """
    l, sign = unpack(">BB", b[:2])
    tail = b[2:]
    n = 0
    for i in array('B', tail[l-1::-1]) :
        n = (n << 8) | i
    if sign :
        n = -n
    return n, tail[l:]


def decode_largebig( b ):
    """ *-----*-----*------*------------------------*
        |  1  |  4  |  1   |    Len                 |
        *-----*-----*------*------------------------*
        | 111 | Len | Sign | d[0],d[1],...,d[Len-1] |
        *-----*-----*------*------------------------* """
    l, sign = unpack(">IB", b[:5])
    tail = b[5:]
    n = 0
    for i in array('B', tail[l-1::-1]):
        n = (n << 8) | i
    if sign:
        n = -n
    return n, tail[l:]


def decode_reference_new( b ):
    """ *-----*-----*------*----------*----*
        |  1  |  2  |  N   |    1     | N' |
        *-----*-----*------*----------*----*
        | 114 | Len | Node | Creation | ID |
        *-----*-----*------*----------*----* """
    l = unpack( ">H", b[:2] )[0]
    node, tail = decode_atom(b[2:])
    return Reference( l, node, tail[1], tail[1:1+(4*l)] ), tail[1+(4*l):]


def decode_atom_small( b ):
    """ *-----*-----*----------*
        |  1  |  1  |    Len   |
        *-----*-----*----------*
        | 115 | Len | AtomName |
        *-----*-----*----------*

    Note that atom names are binary and right-now encoded in 'latin-1'. In
    future this might change.
    """
    name, tail = b[1:1+b[0]], b[1+b[0]:]
    if name == b'true':
        return True, tail
    elif name == b'false':
        return False, tail
    elif name == b"none":
        return None, tail
    return Atom( name.decode('latin-1') ), tail


def decode_newfloat( b ):
    """ *-----*-----*------*
        |  1  |     8      |
        *-----*-----*------*
        |  70 | IEEE Float |
        *-----*-----*------* """
    return unpack( ">d", b[:8])[0], b[8:]


def decode_bitstring( b ):
    """ *-----*-----*------*------*
        |  1  |  4  |  1   | Len  |
        *-----*-----*------*------*
        |  77 | Len | Bits | Data |
        *-----*-----*------*------* """
    l, bits = unpack(">IB", b[:5])
    return BitString( b[5:5+l], bits ), data[5+l:]


decoders = {
    82  : decode_atom_cacheref, # ATOM_CACHE_REFERENCE, not supported
    97  : decode_smallint,      # SMALL_INTEGER_EXT
    98  : decode_int,           # INTEGER_EXT
    99  : decode_float,         # FLOAT_EXT
    100 : decode_atom,          # ATOM_EXT
    101 : decode_reference,     # REFERENCE_EXT, not supported
    102 : decode_port,          # PORT_EXT
    103 : decode_pid,           # PID_EXT
    104 : decode_smalltuple,    # SMALL_TUPLE_EXT, also handles string
    105 : decode_largetuple,    # LARGE_TUPLE_EXT
    106 : decode_nil,           # NIL_EXT
    107 : decode_string,        # STRING_EXT
    108 : decode_list,          # LIST_EXT
    109 : decode_binary,        # BINARY_EXT
    110 : decode_smallbig,      # SMALL_BIG_EXT
    111 : decode_largebig,      # LARGE_BIG_EXT
    114 : decode_reference_new, # REFERENCE_NEW_EXT
    115 : decode_atom_small,    # SMALL_ATOM
    70  : decode_newfloat,      # NEW_FLOAT_EXT
    77  : decode_bitstring,     # BIT_BINARY_EXT
}

#---- Encoder

def invalid_type( typ ) : 
    raise Exception( "Invalid python type when marshalling to erl: %r" % typ )

def encode_term( term ):
    if term == None :   # Unable to gather the type of None
        fn = encoders[None]
    else :
        fn = encoders.get( type(term), invalid_type )
    return fn( term )


#-- Encode handler for each erlang term-binary.

def encode_int( val ):
    """Encode integer data to erlang term. Based on the size of the integer it
    can be encoded as one of the following,
        SMALL_INTEGER_EXT - Single byte integer
        INTEGER_EXT       - Four byte integer
        SMALL_BIG_EXT     - Big integer with maximum of 255 decimal digits
        LARGE_BIG_EXT     - Big integer with maximum of 2^32 decimal digits
    """
    if 0 <= val <= 255 : # SMALL_INTEGER_EXT
        return b'a' + val.to_bytes(1, 'big')

    elif -2147483648 <= val <= 2147483647 : # INTEGER_EXT
        return pack( ">Bi", 98, val )

    if val >= 0 :
        sign = 0
    else :
        sign = 1
        val = -val

    bs = array('B')
    while val > 0 :
        bs.append(val & 0xff)
        val >>= 8

    length = len(bs)
    if length <= 255 : # SMALL_BIG_EXT
        return pack( ">BBB", 110, length, sign ) + bs.tobytes()
    elif length <= 4294967295 : # LARGE_BIG_EXT
        return pack( ">BIB", 111, length, sign ) + bs.tobytes()

    raise Exception( "Invalid integer value" )


def encode_float( val ):
    """Encode python floating point value to erlang term NEW_FLOAT_EXT."""
    return pack( ">Bd", 70, val )


def encode_atom( val ):
    """Encode python's Atom() class to erlang term ATOM_EXT or
    SMALL_ATOM_EXT."""
    return val.encode()


def encode_none( val ):
    """Encode python's None to erlang term SMALL_ATOM_EXT."""
    return Atom('none').encode()


def encode_bool( val ):
    """Encode python's Bool type to erlang term SMALL_ATOM_EXT."""
    return Atom( 'true' if val else 'false' ).encode()


def encode_reference_new( val ):
    """Encode python's Reference() class to erlang term REFERENCE_EXT."""
    return val.encode()


def encode_port( val ):
    """Encode python's Port() class to erlang term PORT_EXT."""
    return val.encode()


def encode_pid( val ):
    """Encode python's Pid() class to erlang term PID_EXT."""
    return val.encode()


def encode_tuple( tup ):
    """Encode python's tuple type to erlang term SMALL_TUPLE_EXT,
    LARGE_TUPLE_EXT."""
    arity = len(tup)
    if arity <= 255:
        header = pack('>BB', 104, arity)
    elif arity <= 4294967295:
        header = pack( ">BI", 105, arity )
    else:
        raise Exception( "Invalid tuple arity while marshalling to erlang" )
    return header + b''.join( map( encode_term, tup ))


def encode_list( lst ):
    """Encode python's list type to erlang term LIST_EXT, NIL_EXT."""
    if lst == [] : return ordnil.to_bytes(1, 'big')
    
    return pack( ">BI", 108, len(lst) ) + \
           b''.join( map( encode_term, lst )) +\
           ordnil.to_binary( 1, 'big' )


def encode_string( val ):
    """Encode python's string type to erlang term STRING_EXT or LIST_EXT."""
    if val == '' : return ordnil.to_bytes(1, 'big')

    try :
        byts = val.encode( 'latin1' )
        return pack( ">BH", 107, len(byts) ) + byts
    except :
        byts = val.encode( 'utf8' )
        return encode_tuple( (ATOM_NSTR, byts) )


def encode_bytes( val ):
    """Encode python's byte type to erlang term BINARY_EXT."""
    return pack(">BI", 109, len(val)) + val


def encode_bitstring( val ):
    """Encode python's BitString class to erlang term BIT_BINARY_EXT."""
    byts = val.to_binary()
    return pack( ">BIB", 77, len(byts), val.bits ) + byts


def encode_dict( val ):
    """Encode python's dictionary type to erlang term LIST_EXT."""
    return encode_term( sorted( list ( val.items() )))

encoders = {
    int       : encode_int,           # SMALL_INTEGER_EXT, INTEGER_EXT,
                                      # SMALL_BIG_EXT, LARGE_BIG_EXT
    float     : encode_float,         # NEW_FLOAT_EXT
    Atom      : encode_atom,          # ATOM_EXT, SMALL_ATOM_EXT
    None      : encode_none,          # ATOM_EXT
    bool      : encode_bool,          # SMALL_ATOM_EXT
    Reference : encode_reference_new, # REFERENCE_NEW_EXT
    Port      : encode_port,          # PORT_EXT
    Pid       : encode_pid,           # PID_EXT
    tuple     : encode_tuple,         # SMALL_TUPLE_EXT, LARGE_TUPLE_EXT
    list      : encode_list,          # LIST_EXT, NIL_EXT
    str       : encode_string,        # { nstr, <binary> } encoded in utf8
                                      # STRING_EXT for latin1
    bytes     : encode_bytes,         # BINARY_EXT
    BitString : encode_bitstring,     # BIT_BINARY_EXT
    dict      : encode_dict           # LIST_EXT
}

