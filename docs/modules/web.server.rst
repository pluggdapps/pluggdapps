:mod:`server` -- HTTP web server based on EPoll.
================================================

.. automodule:: pluggdapps.web.server

Module contents
---------------

.. autoclass:: HTTPEPollServer
    :members: ioloop, start, stop, close_connection
    :show-inheritance:
.. autoclass:: HTTPConnection
    :members: write_callback, close_callback, finish_callback, stream,
              iotimeout, reqdata, chunk, get_ssl_certificate,
              set_close_callback, set_finish_callback, handle_request,
              handle_chunk, close
    :show-inheritance:
.. autofunction:: add_accept_handler
