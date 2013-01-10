# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Plugin definitions for configuration backend-store."""

import sqlite3 

from   pluggdapps.plugin      import Plugin, implements
from   pluggdapps.interfaces  import IConfigDB
import pluggdapps.utils       as h

_default_settings = h.ConfigDict()
_default_settings.__doc__ = (
    "Configuration settings for HTTPRequest implementing IHTTPRequest "
    "interface." )

_default_settings['url'] = {
    'default' : None,
    'types'   : (str,),
    'help'    : "Location of sqlite3 backend to be used for web-admin "
                "configuration."
}

class ConfigSqlite3DB( Plugin ):
    implements( IConfigDB )

    def connect( self, *args, **kwargs ):
        """:meth:`pluggdapps.interfaces.IConfigDB.connect` interface method."""
        self.conn = sqlite3.connect( self['url'] )

    def dbinit( self, settings={}, appsettings=[] ):
        """:meth:`pluggdapps.interfaces.IConfigDB.dbinit` interface method."""
        c = self.conn.cursor()
        # Create the `platform` table if it does not exist.
        c.execute(
            "CREATE TABLE IF NOT EXISTS platform "
                "(section TEXT PRIMARY KEY ASC, settings TEXT)" )
        c.commit()
        if settings :
            self._init_settings( c, settings )

        for netpath, appsett in appsettings :
            c.execute(
                "CREATE TABLE IF NOT EXISTS ? "
                    "(section TEXT PRIMARY KEY ASC, settings TEXT)", 
                netpath )
            c.commit()
            self._init_appsettings( c, netpath, settings )

    def config( self, *args, **kwargs ):
        """:meth:`pluggdapps.interfaces.IConfigDB.config` interface method."""
        if len(args) == 2 :
            section, name = args
            netpath = None
        elif len(args) == 3 :
            netpath, section, name = args
        else :
            raise Exception('Invalid call')
        value = kwargs.get( 'value', None )

        if netpath :    # Configuration for application
            c = self.conn.cursor()
            c.execute('SELECT * FROM ? WHERE section=?', (netpath,section))
            settings = h.json_decode( list(c)[0][1] )
            if value :      # Set configuration
                settings[name] = value
                c.execute( 'INSERT INTO ? VALUES (?, ?)',
                           (netpath, section, h.json_encode(settings)) )
            c.commit()
            return settings[name]
        else :          # Configuration for platform
            c = self.conn.cursor()
            c.execute( 'SELECT * FROM platform WHERE section=?', section )
            settings = h.json_decode( list(c)[0][1] )
            if value :      # Set configuration
                settings[name] = value
                c.execute( 'INSERT INTO platform VALUES (?,?)', 
                           (section, h.json_encode(settings)) )
            c.commit()
            return settings[name]

    def platform( self, settings={} ):
        """:meth:`pluggdapps.interfaces.IConfigDB.platform` interface 
        method."""
        c = self.conn.cursor()
        for section, sett in settings.items() :
            c.execute( 'SELECT * FROM platform WHERE section=?', section )
            s = h.json_decode( list(c)[0][1] )
            s.update( sett )
            c.execute( 'INSERT INTO platform VALUES (?,?)', 
                       (section, h.json_encode(s)) )
        c.commit()

    def application( self, settings=None ):
        """:meth:`pluggdapps.interfaces.IConfigDB.application` interface 
        method."""
        c = self.conn.cursor()
        for netpath, setts in settings.items() :
            for section, sett in setts :
                c.execute( 'SELECT * FROM ? WHERE section=?',
                           (netpath,section) )
                s = h.json_decode( list(c)[0][1] )
                s.update( sett )
                c.execute( 'INSERT INTO ? VALUES (?,?)', 
                           (netpath, section, h.json_encode(s)) )
        c.commit()

    def close( self ):
        """:meth:`pluggdapps.interfaces.IConfigDB.close` interface method."""
        self.conn.close()

    #---- Local methods

    def _init_settings( self, c, settings ):
        c.execute('BEGIN TRANSACTION')
        # First read the section entries from `platform` table before updating
        # it.
        c.execute( "SELECT * FROM platform" )
        dbsettings = { section : h.json_decode(d) for section, d in c }
        for section, d in settings.items() :
            dbsettings.setdefault( section, {} ).update( d )
        # Insert
        for section, d in dbsettings.items() :
            c.execute( "INSERT INTO platform VALUES (?, ?)",
                       (section, h.json_encode(d)) )
        c.execute('END TRANSACTION')

    def _init_appsettings( self, c, netpath, settings ):
        c.execute('BEGIN TRANSACTION')
        # First read the section entries from `platform` table before updating
        # it.
        c.execute( "SELECT * FROM ?", netpath )
        dbsettings = { section : h.json_decode(d) for section, d in c }
        for section, d in settings.items() :
            dbsettings.setdefault( section, {} ).update( d )
        # Insert
        for section, d in dbsettings.items() :
            c.execute( "INSERT INTO ? VALUES (?, ?)",
                       (netpath, section, h.json_encode(d)) )
        c.execute('END TRANSACTION')

