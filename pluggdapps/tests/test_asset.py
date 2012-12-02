# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

import os, sys, unittest
from   os.path import basename

import pluggdapps
from   pluggdapps.utils.asset import parse_assetspec, asset_spec_from_abspath, \
                                     abspath_from_asset_spec 
 
assetmod = sys.modules['pluggdapps.utils.asset']

class UnitTest_Asset( unittest.TestCase ):
    
    def test_parse_assetspec( self ):
        _file = assetmod.__file__
        basenm = basename( _file )
        assert parse_assetspec(_file, None) == (None, _file)
        assert parse_assetspec(basenm, 'pluggdapps') == ('pluggdapps', basenm)
        assert parse_assetspec(basenm, None) == (None, basenm)
        assert parse_assetspec('pluggdapps:asset.py', None) == \
               ('pluggdapps', 'asset.py')

    def test_asset_spec_from_abspath( self ):
        _file = assetmod.__file__
        assert asset_spec_from_abspath(_file, pluggdapps) == \
               'pluggdapps:utils/asset.py'
        assert asset_spec_from_abspath(_file, os) == _file

    def test_abspath_from_asset_spec( self ):
        _file = assetmod.__file__
        assert abspath_from_asset_spec( _file, None ) == _file
        assert abspath_from_asset_spec('pluggdapps:utils/asset.py', '') == \
               _file.rstrip('c')
        assert abspath_from_asset_spec('utils/asset.py', 'pluggdapps') == \
               _file.rstrip('c')


if __name__ == '__main__' :
    unittest.main()
