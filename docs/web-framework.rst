Web application framework
=========================

In recent years developers prefer to use browser, or similar tool, as their
front end and build their application logic on the server side using a wide
variety of techniques. This enables users to publish their application on the
internet as opposed to distributing them. And the most popular design technique 
used by a web developer is Model-View-Controller design pattern implemented in
one of the many popular dynamic languages, like ruby, python, PHP etc.

If you are new to web-frameworks and need more information on MVC design
pattern, you can follow these links,

  *
  *

If you are new to pluggdapps, you are encouraged to read these articles before
continuing further.

  *
  *

The rest of the article is more about the web framework that comes
pre-packaged with pluggdapps distribution and its concepts.

Interfaces
----------

Pluggdapp's web framework is specified by a collection of Interface. Majority
of these interfaces are found in module
:mod:`pluggdapps.web.interfaces.web.interfaces` and a fundamental interface
:class:`IWebApp` is defined in module :mod:`pluggdapps.interfaces`. These
interfaces interact with each other through prescribed method APIs and
collectively they are accessed by :class:`IHTTPConnection` plugin. In other
words, a HTTP request enter the framework through :class:`IHTTPConnection`
plugin.

Journery of a request
---------------------



Application
-----------
