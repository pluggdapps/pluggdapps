# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import unittest
from   copy                 import deepcopy
from   random               import choice
from   array                import array

from   pluggdapps.erlcodec  import assert_true, Atom, BitString, \
                                   encode, decode

class TestERLCodec( unittest.TestCase ):

    def dotest( self, x ):
        level = choice( range(1,9) )
        assert decode( encode( x, compressed=None )) == x

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

    nones = [ None ]
    ints = [ 10, 1000, pow(19, 210), pow(19, 2100) ]
    flts = [ 2.3, 10.222222222222222 ]
    bools = [ True, False ]
    atoms = [ Atom('atom'), Atom('at.-#$om') ]
    strs = [ "hello world", "(汉语/漢語 Hànyǔ" ]
    bins =  [ b'hello world' ]
    bits = [ BitString( b'hello world', 4 ) ]
    nils = [ [] ]
    lsts = [ nones + ints + strs + flts + bools + atoms + bins + bits + nils ]
    tups = [ 
        tuple(nones + ints + strs + flts + bools + atoms + bins + bits + nils),
        tuple( [1] * 300 ),
        tuple(),
    ]
    mixedt = tups[0] + (lsts[0],)
    mixedl = [ nones + ints + strs + flts + bools + atoms + bins + bits + nils ]
    mixedl.append( mixedt )

    def test_none( self ):
        list( map( self.dotest, self.nones ))   # None

    def test_ints( self ):
        list( map( self.dotest, self.ints ))    # Int

    def test_flts( self ):
        list( map( self.dotest, self.flts ))    # Floats

    def test_bools( self ):
        list( map( self.dotest, self.bools ))   # Bools

    def test_atoms( self ):
        list( map( self.dotest, self.atoms ))   # Atoms

    def test_strs( self ):
        list( map( self.dotest, self.strs ))    # String

    def test_bins( self ):
        list( map( self.dotest, self.bins ))    # Binary

    def test_bits( self ):
        list( map( self.dotest, self.bits ))    # Bit string

    def test_bitstring( self ):
        # Bitstring
        x = BitString( b'hello world', 4 )
        y = decode( encode( x ))
        assert x == y
        assert x.bits == y.bits

    def test_nils( self ):
        list( map( self.dotest, self.nils ))    # nils

    def test_lsts( self ):
        list( map( self.dotest, self.lsts ))    # Lists

    def test_tups( self ):
        list( map( self.dotest, self.tups ))    # Lists

    def test_compound( self ):
        # Compound terms
        assert decode( encode( self.mixedt )) == self.mixedt
        assert decode( encode( self.mixedl )) == self.mixedl
        assert decode( encode( tuple( self.mixedl ))) == tuple( self.mixedl )


if __name__ == '__main__' :
    unittest.main()
