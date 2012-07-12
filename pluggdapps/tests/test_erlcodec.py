import unittest
from   copy                 import deepcopy

from   pluggdapps.erlcodec  import assert_true, Atom, String, BitString, \
                                   encode, decode

class TestERLCodec( unittest.TestCase ):

    def test_assert_true( self ) :
        assert_true( True, "Test exception" ) 
        try :
            assert_true( False, "Test exception" )
        except Exception :
            pass


    def test_atom( self ) :
        Atom("hello")
        try :
            Atom("hello" * 100)
        except Exception :
            pass


    def test_string( self ) :
        s = String("hello world")
        assert s == "hello world"


    def test_codec( self ) :
        nones = [ None ]
        ints = [ 10, 1000, pow(19, 210), pow(19, 2100) ]
        strs = [ "hello world", "(汉语/漢語 Hànyǔ" ]
        flts = [ 2.3, 10.222222222222222 ]
        bools = [ True, False ]
        atoms = [ 'atom', 'at.-#$om' ]
        bins =  [ b'hello world' ]
        bits = [ BitString( b'hello world', 4 ) ]
        nils = [ [] ]
        lsts = [ nones + ints + strs + flts + bools + atoms + bins + bits + nils ]
        tups = [ 
            tuple(nones + ints + strs + flts + bools + atoms + bins + bits + nils),
            tuple( [1] * 300 ),
        ]

        def test( x ) :
            assert decode( encode( x )) == x

        list( map( test, nones ))   # None
        list( map( test, ints ))    # Int
        list( map( test, strs ))    # String
        list( map( test, flts ))    # Floats
        list( map( test, bools ))   # Bools
        list( map( test, atoms ))   # Atoms
        list( map( test, bins ))    # Binary
        list( map( test, bits ))    # Bit string
        list( map( test, nils ))    # nils
        list( map( test, lsts ))    # Lists
        list( map( test, tups ))    # Lists


        # Bitstring
        x = BitString( b'hello world', 4 )
        y = decode( encode( x ))
        assert x == y
        assert x.bits == y.bits

        tlist = tups[0] + (lsts[0],)
        mixedl = deepcopy( lsts[0] )
        mixedl.append( tlist )
        assert decode( encode( mixedl )) == mixedl
        assert decode( encode( tuple( mixedl ))) == tuple( mixedl )


if __name__ == '__main__' :
    unittest.main()
