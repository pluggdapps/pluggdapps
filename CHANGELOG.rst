Release changes
===============

0.1dev
------

First release. Provides,

* Component architecture using python meta-classing, a plugin system using 
  interface specifications and a wonderful configuration system.
* Pluggable sub-commands accessible via `pa` script.
* Web-framework to host more than one application in the same environment.
* Documentation available using sphinx.

0.2dev
------

* Releasing DocRoot web-application, to server static web files, as part of 
  Pluggdapps package.
* Releasing IHTTPView plugin `StaticFile` to serve static files.
* New interface-specification defined for in-bound and out-bound
  messages. And two plugins `ResponseHeaders` and `GZipOutBound`, implementing
  IHTTPOutBound interface, are released.
* ETag computation is now part of response-context.
* max_age cache control configuration is supported by IHTTPView plugin
  `StaticFile`.
* For DocRoot application, resource variant mapping can be defined as a python
  list of dictionaries. This will be compiled and used while doing
  content-negotiation with the client.
* Configurable index page and favicon for `DocRoot` web-application.
* Implementing Content negotiation protocol.
* Support for GZip content-encoding added.
* Add plaform method to log debug messages.
* Fixed http_fromdate() helper function.
* Fixed bugs, and cleaned up code, in HTTPEPollServer plugin and HTTPResponse
  plugin


