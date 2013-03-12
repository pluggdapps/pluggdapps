Release changes
===============

0.3dev
------

- Live debug. Interactive debugging to catch exception and introspect stack
  frame via web.
- WebAdmin configuration application.
- ConfigSQlite3DB plugin for storing configuration settings in sqlite3
  database.
- CatchAndDebug plugin re-writes tracebacks involving template tracebacks to
  accurately point mis-behaving template text.
- package documentation using sphinx.
- routemapper configuration to add_views() is now handled by
  matchrouter plugin.
- HTTP content negotiation abstracted into IHTTPNegotiator
  interface and plugin by name `httpnegotiator` is supplied for
  matchrouter.
- match_predicates() method added while resolving view-callables. Right now a
  request resolution to view-callable follows three steps.
  - URL pattern matching
  - match_predicates on add_view arguments and request.
  - Content_negotiation to pick a resource-variant.
- Order of calls to add_view() method is preserved while resolving request to
  view-callable.
- added platform pre-booting feature.
  - First load all pluggdapps packages to create a Pluggdapss() platform, then
    call package() entry point in all pluggdapps packages and finally create
    the platform.
  - package loading during platform pre-booting should happen after all relevant
    pluggdapps modules are imported in __init__.py
  - Package loading during pluggdapps platform pre-boot is now handled by
    an explicit call to pluggdapps.loadpackages() function.
- pluggdapps project static files - logos and css files.
- Documentation for configuration help.
- Gathering files for reloading is now moved to CommandServe plugin, instead
  of handling it in platform classes.
- Improved interactive excaption handling in errorpage.ttl (WebAdmin plugin).
- WebAdmin configuration app is more or less functional.
- package() entry-point now can return 'ttlplugins' info.
- Automatic server restart now monitors .ini files and .ttl files as well.
- request.getparams and request.postparams now provide key,value pairs as
  string.
- Added view callable for serving static files for an application.
- Configured cache directory for ttl template-modules.
- Added scaffolding plugin CommandEnv to create pluggdapps environment. This
  plugin provides the blue-print for ``paenv`` repository which is now
  reponsible for setting up pluggdapps environment for all kind of pluggdapps
  users.

0.2dev
------

- Releasing DocRoot web-application, to server static web files, as part of 
  Pluggdapps package.
- Releasing IHTTPView plugin `StaticFile` to serve static files.
- New interface-specification defined for in-bound and out-bound
  messages. And two plugins `ResponseHeaders` and `GZipOutBound`, implementing
  IHTTPOutBound interface, are released.
- ETag computation is now part of response-context.
- max_age cache control configuration is supported by IHTTPView plugin
  `StaticFile`.
- For DocRoot application, resource variant mapping can be defined as a python
  list of dictionaries. This will be compiled and used while doing
  content-negotiation with the client.
- Configurable index page and favicon for `DocRoot` web-application.
- Implementing Content negotiation protocol.
- Support for GZip content-encoding added.
- Add plaform method to log debug messages.
- Fixed http_fromdate() helper function.
- Fixed bugs, and cleaned up code, in HTTPEPollServer plugin and HTTPResponse
  plugin

0.1dev
------

First release. Provides,

- Component architecture using python meta-classing, a plugin system using 
  interface specifications and a wonderful configuration system.
- Pluggable sub-commands accessible via `pa` script.
- Web-framework to host more than one application in the same environment.
- Documentation available using sphinx.

