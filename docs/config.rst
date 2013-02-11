Configuring pluggdapps
======================

Another fundamental aspect of software systems is to provide a way to
configure and customize their programs. Pluggdapps provide a wonderful
configuration system. It is the responsibility of platform to gather
configuration settings from various sources (like ini-files, data-base etc..)
and make them available for plugins.

So how are these configuration settings related to a plugin ? Well, a plugin
is nothing but a dictionary like object, whose (key,value) pairs are nothing
but its configuration settings. If the settings for a plugin is changed in
the ini-file or in the data-base, it is automatically made available as a
key,value inside the plugin. For example, 
:class:`pluggdapps.web.server.HTTPEPollServer` plugin has configurable 
parameters like, host, port, backlog etc ... the settings are configured
in the ini-file like,

.. code-block:: ini

    [plugin:HTTPEPollServer]
    host = mysite.com
    port = 80
    backlog = 10
    ...

these settings are automatically made available inside the plugin (refered by 
``self``) logic like,

.. code-block:: python

    ....
    sock.listen( self['backlog'] )
    print( "Server listening host and port" % (self['host'], self['port']) )
    ...


From administrator's point of view, platform configuration can be done via ini 
file(s) or through browser using pre-packaged application ``webadmin``, which 
is mounted on the url like http://<hostname>/webadmin.

Master configuration file
-------------------------

Pluggdapps is typically launched using a master configuration file. For
instance, the following command provides a way to start the pluggdapps server
with -c switch supplying master configuration file.

.. code-block:: bash

    pa-env/bin/pa -w -c etc/master.ini serve

master configuration file is expected to provide configuration parameters
organized under two types of sections, ``special-section`` and
``plugin-section``.

**[DEFAULT] special section**

The semantics of DEFAULT section is same as defined by ``configparser`` 
from python standard library. In short, the configured names and their
corresponding values will be applicable to every other section defined in 
the configuration file and all the other configuration files refered by the
master configuration file.

**[pluggdapps] special section**

Platform related configuration is expected to go under this section.

**[mountloc] special section**
    
This section is defined by ``Webapps`` platform, while using ``Pluggdapps``
platform this section is not supported. Administrators can mount web 
application instances on subdomains and script-paths. For Eg,

.. code-block:: ini

    [mountloc]
    pluggdapps.com/webadmin = webadmin, %(here)s/webadmin.ini
    tayra.pluggdapps.com/ = docroot, %(here)s/tayra.ini

The configuration name under [mountloc] section is nothing but url prefix on 
which a web-application instance is mounted. When a web-request enter the 
platform environment it is first resolved for the correct web-application 
under which the request must be handled. On the right hand side of the 
[mountloc] section, a web-application is identified by its name and an 
optional configuration file which shall override configuration settings for 
all plugins invoked under the webapp's context, there by plugins can have
different behaviour for each web-application. 

Note that, application configuration file will accept only plugin sections and 
[DEFAULT] special-section. Any other section will be silently ignore.

**An example master configuration file,**

.. code-block:: ini

  master.ini
  ----------

  [DEFAULT]
  <option> = <value>
  ...

  [pluggdapps]
  <option> = <value>
  ...

  [plugin:<pluginname>]
  <option> = <value>
  ...

  [plugin:<pluginname>]
  ...


Webadmin
--------

Webadmin is pluggdapps application pre-packaged along with ``pluggdapps``
distribution. By default [mountloc] section in ./etc/master.ini will mount
webadmin application as <hostname>/webadmin. It is possible to mount webadmin
app on preferred subdomain/script-path. Like wise, administrators can
access the configuration system through url - http://<hostname>/webadmin and
continue configuring the system. Although, the configured parameters will be
persisted separately by a backend-stored, which by default will be sqlite3.

If you are using ``paenv`` environment to run pluggdapps platform, then
configuration database is persisted as, ``paenv/db/configdb.sqlite3``.

For developers
--------------

If you are not intending to develop plugins for pluggdapps you should do good
just by following previous explanations. In case you intend to develop plugins
for pluggdapps, there are couple of more things you may need to know.

When a plugin class derives from :class:`pluggdapps.plugin.Plugin`, which is 
how they become a plugin, it automatically implements an interface called 
:class:`pluggdapps.plugin.ISettings`. This interface specifies a bunch of 
methods that handles configuration settings for the plugin class.  While the 
platform is booted, the configuration settings are gathered from different 
sources, organised and normalized for plugins' consumption. And when the 
plugins get instantiated (queried by query_*() methods), these settings are 
populated inside the plugin-dictionary.

The cute part about plugin configuration is that, configuration information,
from various sources, are read, parsed aggregated and are automatically
attached to plugin instances when they are instantiated by the platform. Like
mentioned elsewhere, plugin classes although they are defined as regular python
classes must be instantiated only by calling .query_plugin() and
.query_plugins() methods. Every plugin instance created by this way will have
its configuration settings accessible as dictionary of key,value pairs on the
plugin itself. That is, a plugin instance can be accessed like a dictionary, 
where the key name is the configuration name and the value return by the 
key-name is the value of the corresponding configuration name.

**Default configuration**, every plugin classes deriving from :class:`Plugin`
base-classes automatically implements :class:`ISettings` interface. This 
interface specifies that plugins can optionally implement
:meth:`ISettings.default_settings` method and 
:meth:`ISettings.normalize_settings` method. When default_settings() method is
called, it is expected to return a ConfigDict object which will define how a
plugin can be configured.

If a plugin is configured in master ini file, then settings from master-ini
file will override plugin's default settings. If a plugin is configured in 
application configuration file, referred under [mountloc] section, then 
settings from app-ini file will override both default settings and settings 
from master-ini file. Finally, settings from backend data-store will override 
settings from all the other sources.

**Normalizing configuration**, once configuration settings is gathered from
various sources it will be aggregated for each plugin and passed on to
plugin's :meth:`ISettings.normalize_settings` method, which can then apply
data-conversion logic on the settings value and return a curated settings
dictionary.

The normalized settings is preserved along with Interface and Plugin
blue-prints util the system is shutdown.
