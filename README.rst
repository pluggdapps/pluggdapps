Pluggdapps is a :term:`component architecture` in python that can't get any
simpler. A meta framework providing a platform to define interfaces and
implement plugins. It comes with a configuration system, web-framework,
:term:`scaffold`, command-line script and much more ...

Web framework, when used with tayra template language, provide a plugin
system that cut across MVC design pattern. Web-apps can be developed,
packaged and distributed as plugins.

Features
--------

* simple plugin system based on interface specification.
* define framework by specifying interfaces. Implement them as pluggable
  components.
* easy to use configuration system,

  * configuration can be done with one or more .ini files.
  * browser based configuration that can be persisted in a backend store.
  * pluggable backend store for web-based configuration. Uses sqlite3 as default
    backend.

* command line script for administration / testing,

  * sub-command to list matching views for application(s).
  * sub-command to execute unit test-cases.
  * sub-command to start web-server.
  * implement new sub-commands, outside pluggdapps package, as plugins.

* web application framework.

  * web framework, when used with tayra template language, provide a plugin
    system that cut across MVC design pattern.
  * framework is define by a set of interface specification and implemented as
    pluggable components.
  * configure the framework or even replace parts of it.
  * host hundreds of web-application in the same environment by configuring
    mount-points similar to apache virtual-hosts.
  * application can generate urls for other hosted applications.
  * native web server using epoll.
  * automatic server-restart when project files are modified, useful in
    development mode.

* package and distribute plugins as `.egg` files.
* documentation. Every aspect of pluggdapps is adequately documented. Although
  it might be a little difficult for beginners, it is fairly accessible for
  those who are comfortable with python and web-development.
* **License:** `GPLv3 license <http://www.gnu.org/licenses/>`.
* **Requires:** Linux, Python-3.x.
* **Status:** Core design stable. Not expected to change.

