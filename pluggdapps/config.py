# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from   ConfigParser     import SafeConfigParser

from   plugincore       import Plugin, implements
from   interfaces       import IConfig

class IniParser( Plugin ):
    implements( IConfig )

    def settings( self, spec ):
        sc = SafeConfigParser()
        inifile = spec.get( 'url' )
        sc.read( inifile ) if inifile else None
        setts = {}
        setts['DEFAULT'] = sc.defaults()
        setts.update( sc.sections() )
        return sc

