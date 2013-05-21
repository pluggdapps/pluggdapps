Develop with pluggdapps
=======================

This article explains how to make your projects compatible with pluggdapps,
define `interfaces` and author `plugins`.

Create pluggdapps project
-------------------------

Pluggdapps uses python3, its stdlib, setuptools and virtual-environment to
create a notion of platform. A platform is an environment, a run-time, using
which developers can create programs and distribute them to other machines as
long as they have the same virtual environment.

Pluggdapps project is packaged using setuptools and while doing so, it is
expected that ``[pluggdapps] package`` entry point is defined, for eg.,

.. code-block:: python
    :linenos:

    # setup.py
    ...
    setup(
        ...
        ...
        entry_points={                          # setuptools
            'pluggdapps' : [
                'package=<module.path>:<function-name>',
            ]
        },
        ...
    )

Typically, a pluggdapps project will define the package entry-point function
as ``package``. Presence of this entry point will indicate that the package is
part of pluggdapps environment. This entry point will be called during
pluggdapps boot-time, and expected to return a dictionay of package
information.

**Example package**

Tayra is a templating language that is distributed as pluggdapps package, the
following code is taken from ``tayra/__init__.py`` package file,

.. code-block:: python
    :linenos:

    def package( pa ) :
        loadttls( pa, template_plugins )
        return {
            'ttlplugins' : template_plugins,
        }

Note that tayra package is using this entry point to load template plugins and
return a dictionary of information about them.

Below is the list of keys that can be returned as package information. Unless
otherwise explicitly mentioned these keys are optional.

``ttlplugins``,
    List of template files with absolute path names. Presence of this key
    indicates that the package is providing tayra template plugins.


Specify interface 
-----------------

Every pluggdapps package can have any number of interface-specification
defined in them. Just make sure that modules containing these interface
specifications are imported by the package-init file -
`<package-path>/__init__.py`. An example interface specification that define
callback methods to persist configuration settings on a backed data-store,

.. code-block:: python
    :linenos:

    class IConfigDB( Interface ):
        """Interface specification to persist / access platform configuration to
        backend data-store or database. When platform gets booted and if
        config-backend is available, then configuration settings from datastore
        will override settings from `.ini` files."""

        def connect():
            """Do necessary initialization to connect with data-store."""

        def dbinit( *args, **kwargs ): #*
            """If datastore does not exist, create one. Also intialize
            configuration tables for each mounted application under
            [mountloc] section. Expect this method to be called when ever
            platform
            starts-up. For more information refer to corresponding plugin's
            documentation.
            """

        def config( **kwargs ): #**
            """Get or set configuration parameter for platform. For more
            information refer to corresponding plugin's documentation."""

        def close():
            """Reverse of :meth:`connect`."""

other than definig the methods, explaining its purpose as doc-strings,
interface specification doesn't do much. The above interface will be used by
platform class during pluggdapps boot-time.

Create plugin
-------------

Plugins derive from :class:`Plugin` base class and implement one or more
interfaces. Following is a plugin class implementing `IConfigDB` interface

.. code-block:: python

    class ConfigSqlite3DB( Plugin ):
        """Backend interface to persist configuration information in sqlite3
        database."""

        implements( IConfigDB )

        def __init__( self ):
            self.conn = sqlite3.connect( self['url'] ) if self['url'] else None

        def connect( self, *args, **kwargs ): #*
            """:meth:`pluggdapps.interfaces.IConfigDB.connect` interface
            method."""
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

        def config( self, **kwargs ): #**
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

            - if netpath, section, name and value kwargs are supplied, will
              update config-parameter `name` under webapp's `section` with
              `value`.  Return the updated value.
            - if netpath, section, name kwargs are supplied, will return
              configuration `value` for `name` under webapp's `section`.
            - if netpath, section kwargs are supplied, will return dictionary
              of all configuration parameters under webapp's section.
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
            """:meth:`pluggdapps.interfaces.IConfigDB.close` method."""
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

some of the points that you should make note of,

* every plugin class should ultimately derive from :class:`Plugin` base class
  either directly, or indirectly through other plugins.
* use `implements()` API to declare one or more interfaces implemented by this
  plugin. More than one interfaces can be passed as variable number of
  positional arguments to `implements()` API.
* always define interface methods specified by interfaces unless they have a
  default behaviour implemented by the base classes.
* plugins can define attributes and manage their context with them. Attributes
  are alive for the life-span of the plugin object.
* every plugin automatically implements `default_settings()` class-method and
  `normalize_settings()` class-method. The semantics of these methods are
  explained by :class:`pluggdapps.plugin.ISettings` interface spec.

**Overriding plugin methods**

When a plugin class derives from a base plugin class, overriding its interface
methods and non-interface methods are similar to python inheritance concepts,
except for `__init__` method. For example, let us say that a plugin class
`MyPlugin` inherits from another plugin class `YourPlugin`, it must look
something similar to following snippet.

.. code-block:: python
    :linenos:

    class YourPlugin( Plugin ):
        def __init__( self, arg2, arg3 ):
            pass

    class MyPlugin( YourPlugin ):
        def __init__( self, arg1, arg2, arg3 ):
            self._super_init( __class__, arg2, arg3 )

instead of using `super()` built-in function to access base-class'
`__init__()` method, you must always use `self._super_init()` method to
call plugin's base-class' `__init__()` method.

