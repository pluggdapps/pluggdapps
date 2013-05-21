:mod:`response` -- HTTP Response object.
========================================

.. automodule:: pluggdapps.web.response

Module contents
---------------

.. autoclass:: HTTPResponse
    :members: start_response, write_buffer, flush_callback,
              finish_callback, finished, __init__, set_status,
              set_header, add_header, set_trailer, add_trailer,
              set_cookie, set_secure_cookie, clear_cookie,
              clear_all_cookies, set_finish_callback, has_finished,
              isstarted, ischunked, write, flush, httperror, render,
              chunk_generator
    :show-inheritance:
