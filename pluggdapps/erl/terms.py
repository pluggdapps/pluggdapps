# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

__all__ = [ 'Atom','BitString', 'Reference', 'Port', 'Pid', 
            # Standar atoms used for marshaling request.
            'ATOM_OK', 'ATOM_ERROR', 'ATOM_GET', 'ATOM_POST', 'ATOM_NSTR',
            'ATOM_UTF8', 'ATOM_LOGERROR', 'ATOM_LOGINFO', 'ATOM_LOGWARN',
            'ATOM_LOOPBACK', 'ATOM_APPY', 'ATOM_QUERY_PLUGIN',
            'ATOM_PLUGIN_ATTRIBUTE', 'ATOM_PLUGIN_METHOD' ]


class Atom( str ):
    """Erlang's atom term represented in python."""

    def __new__( cls, s ):
        assert len(s) <= 255
        return super().__new__( cls, s )

    def __repr__( self ):
        return "Atom(%s)" % self

    def encode( self ):
        b = self.encode('latin-1')
        if len(b) <= 255 :  # SMALL_ATOM_EXT
            return pack( ">BB", 115, len(b) ) + b
        else :  # ATOM_EXT
            return pack( ">BH", 100, len(b) ) + b


class BitString( bytes ):
    """Erlang's Bit string term represented in python."""

    def __new__( cls, s, bits ):
        """Create a bit string instance,
        
        `s`,
            Bytes representing the binary part of bit-string
        `bits`,
            count value from 0 to 8 representing valid number bits in the last
            byte of `s`.
        """
            
        obj = super().__new__( cls, s )
        obj.bits = bits
        obj.s = s
        return obj

    def to_binary( self ):
        s, bits = self.s, self.bits
        if s and bits == 0 :
            return s[:-1]
        elif s and bits == 8 :
            return s
        elif s :
            i = s[-1] & ( (pow(2,bits)-1) << (8-bits) )
            return s[:-1] + i.to_bytes(1, 'big')
        return s

    def value( self ):
        s, bits = self.s, self.bits
        if s and bits == 0 :
            return s[:-1]
        elif s and bits == 8 :
            return s
        elif s and bits :
            i = ( s[-1] & ( (pow(2,bits)-1) << (8-bits) )) >> (8-bits)
            return s[:-1] + i.to_bytes(1, 'big')
        return s

    def __eq__( self, other ):
        if isinstance( other, self.__class__ ):
            return self.value() == other.value()
        else :
            return False

    def __ne__( self, other ):
        return not self.__eq__( other )

    def __repr__(self):
        return "BitString(%s, %s)" % ( self.value(), super().__repr__() )


class Reference( object ):
    """Erlang's reference term represented in python."""
    def __init__( self, length, node, creation, ID ):
        self.length = length
        self.node = node
        self.creation =creation
        self.ID = ID

    def encode( self ):
        """Encode this object into erlang's REFERENCE_NEW_EXT."""
        node = encode_atom( self.node )
        return pack( ">BH", 114, self.length ) + node + \
               pack( ">B", self.creation ) + self.ID


class Port( object ):
    """Erlang's port term represented in python."""
    def __init__( self, node, ID, creation ):
        self.node = node
        self.creation = creation
        self.ID = ID

    def encode( self ):
        """Encode this object into erlang's PORT_EXT."""
        node = encode_atom( self.node )
        return pack(">B", 102) + node + self.ID + pack(">B", self.creation) 
    

class Pid( object ):
    """Erlang's process-id term represented in python."""
    def __init__( self, node, ID, serial, creation ):
        self.node = node
        self.creation = creation
        self.ID = ID
        self.serial = serial
        
    def encode( self ):
        """Encode this object into erlang's PID_EXT."""
        node = encode_atom( self.node )
        return pack( ">B", 103 ) + node + self.ID + self.serial + \
               pack( ">B", self.creation )
    

#-- Pre-defined atoms used for marshalling data

# Methods
ATOM_GET              = Atom('get')
ATOM_POST             = Atom('post')
ATOM_LOOPBACK         = Atom('loopback')
ATOM_APPY             = Atom('apply')
ATOM_QUERY_PLUGIN     = Atom('query_plugin')
ATOM_PLUGIN_ATTRIBUTE = Atom('plugin_attribute')
ATOM_PLUGIN_METHOD    = Atom('plugin_method')

ATOM_NSTR     = Atom('nstr')
ATOM_UTF8     = Atom('utf8')

ATOM_OK       = Atom('ok')
ATOM_ERROR    = Atom('error')

ATOM_LOGERROR = Atom('logerror')
ATOM_LOGINFO  = Atom('loginfo')
ATOM_LOGWARN  = Atom('logwarn')

