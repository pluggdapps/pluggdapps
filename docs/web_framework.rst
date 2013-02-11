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

Web framework
-------------

A frame-work is a software system encouraging a specific set of design pattern
for program development, which can be developed independantly, while still be
able inter-operate with other programs that are being developed using the same
framework. In pluggdapps, frameworks are defined by specifying interfaces
that can inter-operate with each other, and by putting together desired set of 
interfaces we get a complete framework similar to Rails or Django.

Right now we have a web-framework packaged along with pluggdapps, whose
framework interfaces are specified in :mod:`pluggdapps.web.webinterfaces` and
a more fundamental interface specified in 
:class:`pluggdapps.interfaces.IWebApp`. Putting together they define
pluggdapps web-framework. And the framework is implemented by a
collection of plugins under :mod:`pluggdapps.web` directory. Other than 
learning to configure them, developers, for most part, shouldn't worry about 
the supplied interfaces or plugins. Only when there is a need to customize or
replace part of the frame-work definition or its implementation, we expect
them to dig deeper.

Savvy developers can jump to module documentation, built with sphinx, and
learn the nuts and bolts of pluggdapps' web-framework. Others had to wait for 
a more eloborate, easy to read, articles on pluggdapps web-application
development. Just to tickle your interest, we might add that **pluggdapps is
aiming to unify the MVC design pattern and a plugin system - seamlessly.**

pa -w -c <master.ini>


Web-application platform:
-------------------------

Implemented by :class:`Webapps` class (which derives from base platform class
:class:`Pluggdapps`), it can host any number web-application, and/or instance
of same web-application, in a single python environment. Every web-application
is a plugin implementing :class:`pluggdapps.interfaces.IWebApp` interface.
When plugins are instantiated by a webapp plugin, either directly or
indirectly, the instantiated plugins are automatically supplied with
**.webapp** attribute.

Web-applications can be mounted, hosted, on a netlocation and script-path
(collectively called as ``netpath``). This is configured under **[mountloc]**
special section. While mounting web-applications under [mountloc] additional 
configuration files can be referred.

Example [mountloc] section,::

  [mountloc]
  pluggdapps.com/issues = <appname>, <ini-file>
  tayra.pluggdapps.com/issues = <appname>, <ini-file>
  tayra.pluggdapps.com/source = <appname>, <ini-file>

The referred configuration files are exclusive to the scope of the mounted
application, and shall not contain any special sections, except `[DEFAULT]`,
unless otherwise explicitly mentioned. When a plugin is instantiated in the
context of a web-application, configuration settings from application-ini-file
will override settings from the master-ini-file.

Finally the platform can be started like,::

  pa = Webapps.boot( args.config )

where ``args.config`` locates the master-ini file

Dynamic plugins :

  There is also an option to create plugin blue-prints dynamically and this
  option can be carried out by package() entry point implemented by every
  pluggdapps pacakge. Note that this entry point is called in the context of
  platform object ``pa`` which is only a partial implementation platform since
  they do not contain the dynamic plugins. Once all entry points are called, a
  fully-aware platform object is created.
