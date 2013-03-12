:mod:`request` -- HTTP Request object.
======================================

.. automodule:: pluggdapps.web.request

Module contents
---------------

.. autoclass:: HTTPRequest
    :members: content_type, __init__, supports_http_1_1,
              get_ssl_certificate, get_cookie, get_secure_cookie,
              has_finished, ischunked, handle, onfinish, urlfor,
              pathfor, appurl
    :show-inheritance:
