:mod:`interfaces` -- Web framework Interface specs.
===================================================

.. automodule:: pluggdapps.web.interfaces


Module contents
---------------

.. autoclass:: IHTTPRouter
    :members: onboot, add_view, route, urlpath, onfinish
    :show-inheritance:
.. autoclass:: IHTTPContentNegotiation
.. autoclass:: IHTTPNegotiator
    :members: negotiate
    :show-inheritance:
.. autoclass:: IHTTPResource
    :members: __call__
    :show-inheritance:
.. autoclass:: IHTTPCookie
    :members: parse_cookies, set_cookie, create_signed_value,
              decode_signed_value
    :show-inheritance:
.. autoclass:: IHTTPRequest
    :members: httpconn, method, uri, version, headers, body, chunks,
              trailers, uriparts, cookies, getparams, postparams,
              multiparts, params, files, session, cookie, response,
              router, matchdict, view, resource, receivedat,
              finishedat, __init__, supports_http_1_1,
              get_ssl_certificate, get_cookie, get_secure_cookie,
              has_finished, ischunked, handle, onfinish, urlfor,
              pathfor, appurl
    :show-inheritance:
.. autoclass:: IHTTPResponse
    :members: statuscode, reason, version, headers, body, chunks,
              chunk_generator, trailers, setcookies, request, context,
              media_type, charset, language, content_coding,
              __init__, set_status, set_header, add_header,
              set_trailer, add_trailer, set_cookie, 
              set_secure_cookie, clear_cookie, clear_all_cookies,
              set_finish_callback, has_finished, isstarted, ischunked,
              write, flush, httperror, render, chunk_generator
    :show-inheritance:
.. autoclass:: IHTTPView
    :members: viewname, view, __init__, __call__, onfinish
    :show-inheritance:
.. autoclass:: IHTTPInBound
    :members: transform
    :show-inheritance:
.. autoclass:: IHTTPOutBound
    :members: transform
    :show-inheritance:
.. autoclass:: IHTTPRenderer
    :members: render
    :show-inheritance:
.. autoclass:: IHTTPLiveDebug
    :members: render
    :show-inheritance:
