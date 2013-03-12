# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

"""Platform can be configured via ini files. For ease of administration,
platform can also be configured via web as well, where the configuration
information (basically the key, value pair) will be persisted by a backend
store like `sqlite3`.

Note that configuration parameters from database backend will override 
default_settings and configurations from ini file.
"""

# TODO :
#   What are the special sections stored ? Are the special sections
#   store for <netpath> tables as well ? Section names are prefixed with
#   'plugin:' ?
#           Document them.

import sqlite3

from   pluggdapps.plugin      import Plugin, implements
from   pluggdapps.interfaces  import IConfigDB
import pluggdapps.utils       as h

class ConfigSqlite3DB( Plugin ):
    """Backend interface to persist configuration information in sqlite3
    database.
    
    Settings are stored in tables, one table for each mounted application.
    ``netpath`` name (contains subdomain-hostname / script), on which
    application is mounted, will be used as table-name. Table structure,

    <netpath> table :

        +-------------------+-------------------------------+
        |   section         |   settings                    |
        +===================+===============================+
        |  section-name     | JSON string of settings       |
        +-------------------+-------------------------------+

    where,

    * section-name can be `special section` or plugin section that starts with
      ``plugin:`` prefix.
    * JSON string contains key,value pairs of configuration settings only for
      those parameters that were updated using web-frontend.
    * along with netpaths, a special table called ``platform`` will be created.
      Platform wide settings, overriden by settings from master-ini file, will
      be stored in this table.
    * special sections will be present only in case of ``platform`` table.
      For other `netpath` tables, other that ``[DEFAULT]`` section, no special
      section will be stored.
    """

    implements( IConfigDB )

    def __init__( self ):
        self.conn = sqlite3.connect( self['url'] ) if self['url'] else None

    def connect( self, *args, **kwargs ):
        """:meth:`pluggdapps.interfaces.IConfigDB.connect` interface method."""
        if self.conn == None and self['url'] :
            self.conn = sqlite3.connect( self['url'] )

    def dbinit( self, netpaths=[] ):
        """:meth:`pluggdapps.interfaces.IConfigDB.dbinit` interface method.
        
        Optional key-word argument,

        ``netpaths``,
            list of web-application mount points. A database table will be
            created for each netpath.
        """
        if self.conn == None : return None

        c = self.conn.cursor()
        # Create the `platform` table if it does not exist.
        c.execute(
            "CREATE TABLE IF NOT EXISTS platform "
                "(section TEXT PRIMARY KEY ASC, settings TEXT);" )
        self.conn.commit()

        for netpath in netpaths :
            sql = ( "CREATE TABLE IF NOT EXISTS '%s' "
                        "(section TEXT PRIMARY KEY ASC, settings TEXT);" ) %\
                  netpath
            c.execute( sql )
            self.conn.commit()

    def config( self, **kwargs ):
        """:meth:`pluggdapps.interfaces.IConfigDB.config` interface method.

        Keyword arguments,

        ``netpath``,
            Netpath, including subdomain-hostname and script-path, on which
            web-application is mounted. Optional.

        ``section``,
            Section name to get or set config parameter. Optional.

        ``name``,
            Configuration name to get or set for ``section``. Optional.

        ``value``,
            If present, this method was invoked for setting configuration
            ``name`` under ``section``. Optional.

        - if netpath, section, name and value kwargs are supplied, will update
          config-parameter `name` under webapp's `section` with `value`.
          Return the updated value.
        - if netpath, section, name kwargs are supplied, will return
          configuration `value` for `name` under webapp's `section`.
        - if netpath, section kwargs are supplied, will return dictionary of 
          all configuration parameters under webapp's section.
        - if netpath is supplied, will return the entire table as dictionary
          of sections and settings.
        - if netpath is not supplied, will use `section`, `name` and `value`
          arguments in the context of ``platform`` table.
        """
        if self.conn == None : return None

        netpath = kwargs.get( 'netpath', 'platform' )
        section = kwargs.get( 'section', None )
        name = kwargs.get( 'name', None )
        value = kwargs.get( 'value', None )

        c = self.conn.cursor()
        if section :
            c.execute(
                "SELECT * FROM '%s' WHERE section='%s'" % (netpath,section))
            result = list(c) 
            secsetts = h.json_decode( result[0][1] ) if result else {}
            if name and value :
                secsetts[name] = value
                secsetts = h.json_encode(secsetts)
                c.execute( "DELETE FROM '%s' WHERE section='%s'" % 
                           (netpath, section) )
                c.execute( "INSERT INTO '%s' VALUES ('%s', '%s')" %
                           (netpath, section, secsetts) )
                self.conn.commit()
                rc = value
            elif name :
                rc = secsetts[name]
            else :
                rc = secsetts
        else :
            c.execute( "SELECT * FROM '%s'" % (netpath,) )
            rc = {  section : h.json_decode( setts )
                                        for section, setts in list(c) }
        return rc

    def close( self ):
        """:meth:`pluggdapps.interfaces.IConfigDB.close` interface method."""
        if self.conn :
            self.conn.close()

    #---- ISettings interface methods

    @classmethod
    def default_settings( cls ):
        """:meth:`pluggdapps.plugin.ISettings.default_settings` interface
        method.
        """
        return _default_settings

    @classmethod
    def normalize_settings( cls, sett ):
        """:meth:`pluggdapps.plugin.ISettings.normalize_settings` interface
        method.
        """
        return sett

_default_settings = h.ConfigDict()
_default_settings.__doc__ = ConfigSqlite3DB.__doc__

_default_settings['url'] = {
    'default'   : '',
    'types'     : (str,),
    'help'      : "Location of sqlite3 backend file. Will be passed to "
                  "sqlite3.connect() API. Can be modified only in the .ini "
                  "file.",
    'webconfig' : False,
}

