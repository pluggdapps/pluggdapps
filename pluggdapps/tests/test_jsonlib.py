# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy


import os, sys, unittest
from   os.path import basename

import pluggdapps
from   pluggdapps.utils.jsonlib import json_encode, json_decode
 
obj = {
    'str'            : [ 1, 'str', 10.2, (1,2), ],
    '汉语/漢語 Hàny' : [ 1, 'str', 10.2, (1,2), ],
    'bytes'          : [ 1, 'str', 10.2, (1,2), ],
}
ref = {
    'str'            : [ 1, 'str', 10.2, [1,2], ],
    '汉语/漢語 Hàny' : [ 1, 'str', 10.2, [1,2], ],
    'bytes'          : [ 1, 'str', 10.2, [1,2], ],
}

class UnitTest_JsonLib( unittest.TestCase ):

    def test_jsoncodec( self ):
        res = json_encode(obj)
        assert ref == json_decode( res )
        res = json_encode(obj, encoding='utf8')
        assert ref == json_decode(res, encoding='utf8')
        res = json_encode(obj, encoding='latin1')
        assert ref == json_decode(res, encoding='latin1')
    
if __name__ == '__main__' :
    unittest.main()

