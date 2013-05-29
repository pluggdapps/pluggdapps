:mod:`interfaces` -- Interface specifications.
==============================================

.. automodule:: pluggdapps.interfaces

Module contents
---------------

.. autoclass:: IConfigDB
    :members: connect, dbinit, config, close
    :show-inheritance:
.. autoclass:: ICommand
    :members: description, usage, cmd, subparser, handle
    :show-inheritance:
.. autoclass:: IHTTPServer
    :members: sockets, connections, version, start, stop,
              close_connection
    :show-inheritance:
.. autoclass:: IHTTPConnection
    :members: conn, address, server, product, version, request,
              get_ssl_certificate, set_close_callback,
              set_finish_callback, handle_request, handle_chunk,
              write, close
    :show-inheritance:
.. autoclass:: IWebApp
    :members: instkey, appsettings, netpath, baseurl, router, cookie,
              livedebug, in_transformers, out_transformers, startapp,
              dorequest, dochunk, onfinish, shutdown, urlfor, pathfor
    :show-inheritance:
.. autoclass:: IScaffold
    :members: description, query_cmdline, generate, printhelp
    :show-inheritance:
.. autoclass:: ITemplate
    :members: render
    :show-inheritance:
