"""
Erlang external term format.
    Refer : http://www.erlang.org/doc/apps/erts/erl_ext_dist.html
"""

from   struct     import pack, unpack
from   array      import array
from   zlib       import decompressobj, compress
from   datetime   import datetime
import builtins

# TODO :
#   * Unable to gather type of None.


ordnil = ord( "j" )

class ErrorERLCodec( Exception ):
    """Exception class for all erl codec related errors"""


def assert_true( val, msg=None ) :
    msg = msg or "Assertion failed in marshalling erlang terms"
    if val != True : 
        raise ErrorERLCodec( msg )


class Atom( str ):
    """Erlang's atom."""

    def __new__( cls, s ):
        assert_true( len(s) <= 255 )
        return super().__new__( cls, s )

    def __repr__( self ):
        return "Atom(%s)" % self

    def tobytes( self ):
        return self.encode('latin-1')


class BitString( bytes ):
    """Erlang's Bit string."""

    def __new__( cls, s, bits ):
        obj = super().__new__( cls, s )
        obj.bits = bits
        return obj

    def __repr__(self):
        return "BitString(%s, %s)" % ( self.bits, super().__repr__() )


#---- Decoder

def decode( bstr ):
    """Decode Erlang external term."""
    assert_true( len(bstr) >= 1 )

    version = bstr[0]
    assert_true( version == 131, "Unknown protocol version: %i" % version )

    if bstr[1:2] != b'\x50':   # un-compressed term
        return decode_term( bstr[1:] )[0]

    # Compressed term
    assert_true( len(bstr) >= 6 )
    d = decompressobj()
    term_string = d.decompress( bstr[6:] ) + d.flush()
    uncompressed_size = unpack( '>I', bstr[2:6] )[0]
    assert_true( 
            len(term_string) == uncompressed_size,
            "Invalid compressed tag, "
            "%d bytes but got %d" % (uncompressed_size, len(term_string))
    )
    # tail data returned by decode_term() can be simple ignored
    # Note : d.unused_data might contain something ?!
    return decode_term( term_string )[0]


def decode_term( bstr ):
    assert_true( len(bstr) >= 1 )
    tag, tail = bstr[0], bstr[1:]
    if tag != 106 :     # Expect a tail only if tag is not Nil, a `[]`
        assert_true( bool(tail) )
    decoder = decoders[tag]
    def fail( tail ):
        raise ValueError( "Unsupported data tag: %i" % tag )
    return decoders.get( tag, fail )( tail )


def decode_newfloat( tail ):
    return unpack( ">d", tail[:8])[0], tail[8:]


def decode_bitstring( tail ):
    assert_true( len(tail) >= 5 )
    length, bits = unpack(">IB", tail[:5])
    tail1 = tail[5:]
    assert_true( len(tail1) >= length )
    return BitString(tail1[:length], bits), tail1[length:]


def decode_smallint( tail ):
    return ord(tail[:1]), tail[1:]


def decode_int( tail ):
    assert_true( len(tail) >= 4 )
    return unpack( ">i", tail[:4] )[0], tail[4:]


def decode_float( tail ):
        return float(tail[:31].split("\x00", 1)[0]), tail[31:]


def decode_atom( tail ):
    assert_true( len(tail) >= 2 )
    length, tail = unpack( ">H", tail[:2] )[0], tail[2:]
    assert_true( len(tail) >= length )
    name, tail = tail[:length], tail[length:]
    if name == b"true":
        return True, tail
    elif name == b"false":
        return False, tail
    elif name == b"none":
        return None, tail
    return Atom( name.decode('latin-1') ), tail


def decode_smalltuple( tail ):
    assert_true( bool(tail) )
    arity, tail = tail[0], tail[1:]
    lst = []
    while arity > 0:
        term, tail = decode_term(tail)
        lst.append(term)
        arity -= 1
    return tuple(lst), tail


def decode_largetuple( tail ):
    assert_true( len(tail) >= 4 )
    arity, tail = unpack(">I", tail[:4])[0], tail[4:]
    lst = []
    while arity > 0:
        term, tail = decode_term(tail)
        lst.append(term)
        arity -= 1
    return tuple(lst), tail


def decode_nil( tail ):
    return [], tail


def decode_string( tail ):
    assert_true( len(tail) >= 2 )
    length, tail1 = unpack( ">H", tail[:2] )[0], tail[2:]
    assert_true( len(tail1) >= length )
    return tail1[:length].decode('utf8'), tail1[length:]


def decode_list( tail ):
    assert_true( len(tail) >= 4 )
    length = unpack( ">I", tail[:4] )[0]
    tail, lst = tail[4:], []
    while length > 0:
        term, tail = decode_term(tail)
        lst.append(term)
        length -= 1
    _, tail = decode_term(tail)
    return lst, tail


def decode_binary( tail ):
    assert_true( len(tail) >= 4 )
    length, tail = unpack( ">I", tail[:4] )[0], tail[4:]
    assert_true( len(tail) >= length )
    return tail[:length], tail[length:]


def decode_smallbig( tail ):
    assert_true( len(tail) >= 2 )
    length, sign = unpack(">BB", tail[:2])
    tail = tail[2:]
    assert_true( len(tail) >= length )
    n = 0
    for i in array('B', tail[length-1::-1]):
        n = (n << 8) | i
    if sign:
        n = -n
    return n, tail[length:]


def decode_largebig( tail ):
    assert_true( len(tail) >= 5 )
    length, sign = unpack(">IB", tail[:5])
    tail = tail[5:]
    assert_true( len(tail) >= length )
    n = 0
    for i in array('B', tail[length-1::-1]):
        n = (n << 8) | i
    if sign:
        n = -n
    return n, tail[length:]


decoders = {
    70  : decode_newfloat,      # NEW_FLOAT_EXT
    77  : decode_bitstring,     # BIT_BINARY_EXT
    97  : decode_smallint,      # SMALL_INTEGER_EXT
    98  : decode_int,           # INTEGER_EXT
    99  : decode_float,         # FLOAT_EXT
    100 : decode_atom,          # ATOM_EXT
    104 : decode_smalltuple,    # SMALL_TUPLE_EXT
    105 : decode_largetuple,    # LARGE_TUPLE_EXT
    106 : decode_nil,           # NIL_EXT
    107 : decode_string,        # STRING_EXT
    108 : decode_list,          # LIST_EXT
    109 : decode_binary,        # BINARY_EXT
    110 : decode_smallbig,      # SMALL_BIG_EXT
    111 : decode_largebig,      # LARGE_BIG_EXT
}


#---- Encoder

def encode( term, compressed=False ):
    encoded_term = encode_term( term )
    # False and 0 do not attempt compression.
    if compressed:
        zlib_term = compress( encoded_term, compressed )
        if len(zlib_term) + 5 <= len(encoded_term):
            # compressed term is smaller
            return b'\x83\x50' + pack('>I', len(encoded_term)) + zlib_term
    return b"\x83" + encoded_term


def encode_term( term ):
    def fail( term ) : 
        raise ValueError( "Unsupported term : %r" % type(term) )
    if term == None :   # Unable to gather the type of None
        fn = encoders[None]
    else :
        fn = encoders.get( type(term), fail )
    return fn( term )


def encode_none( term ):
    return pack(">BH", 100, 4) + b"none"


def encode_int( term ):
    if 0 <= term <= 255:
        return b'a' + term.to_bytes(1, 'big')

    elif -2147483648 <= term <= 2147483647:
        return pack( ">Bi", 98, term )

    if term >= 0 :
        sign = 0
    else:
        sign = 1
        term = -term

    bs = array('B')
    while term > 0 :
        bs.append(term & 0xff)
        term >>= 8

    length = len(bs)
    if length <= 255:
        return pack( ">BBB", 110, length, sign ) + bs.tobytes()
    elif length <= 4294967295:
        return pack( ">BIB", 111, length, sign ) + bs.tobytes()

    raise ValueError( "Invalid integer value" )


def encode_float( term ):
    return pack( ">Bd", 70, term )


def encode_bool( term ):
    term = b"true" if term else b"false"
    return pack( ">BH", 100, len(term) ) + term


def encode_atom( term ):
    return pack( ">BH", 100, len(term) ) + term.tobytes()


def encode_string( term ):
    if not term :
        return ordnil
    utf8 = term.encode('utf8')
    if len(utf8) < 65535 :
        return pack( ">BH", 107, len(utf8) ) + utf8
    else :
        return encode_list( term )


def encode_bytes( term ):
    return pack(">BI", 109, len(term)) + term


def encode_bitstring( term ):
    return pack( ">BIB", 77, len(term), term.bits ) + term


def encode_list( term ):
    if term :
        elements = b''.join( map( encode_term, term + [ordnil] ))
        return pack( ">BI", 108, len(term) ) + elements
    else :
        return ordnil.to_bytes(1, 'big')


def encode_tuple( term ):
    arity = len(term)
    if arity <= 255:
        header = pack('>BB', 104, arity)
    elif arity <= 4294967295:
        header = pack( ">BI", 105, arity )
    else:
        raise "Invalid tuple arity"
    return header + b''.join( map( encode_term, term ))


def encode_dict( term ):
    # encode dict as proplist, but will be orddict compatible if keys
    # are all of the same type.
    return encode_term( sorted(term.iteritems()) )


def encode_datetime( term ):
    date = (term.year, term.month, term.day)
    time = (term.hour, term.minute, term.second)
    return encode_term(( date, time))


encoders = {
    BitString : encode_bitstring, # Python bit-string
    int       : encode_int,       # Python integer
    float     : encode_float,     # Python float
    Atom      : encode_atom,      # Python atom
    tuple     : encode_tuple,     # Python tuple
    None      : encode_none,      # Python none
    str       : encode_string,    # Python string (unicode)
    bytes     : encode_bytes,     # Python bytes a.k.a binary
    bool      : encode_bool,      # Python boolean
    list      : encode_list,      # Python list
    dict      : encode_dict,      # Python dictionary
    datetime  : encode_datetime,  # Python Date-Time
}

