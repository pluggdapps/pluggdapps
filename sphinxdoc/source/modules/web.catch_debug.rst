:mod:`catch_debug` -- Interactive web debugging.
================================================

.. automodule:: pluggdapps.web.catch_debug

Module contents
---------------

.. autoclass:: CatchAndDebug
    :members: render, collectFrame, collectException
    :show-inheritance:
.. autoclass:: CollectedException
    :members: frames, exception_type, exception_formatted,
              exception_value, identification_code, date, extra_data
    :show-inheritance:
.. autoclass:: ExceptionFrame
    :members: modname, filename, lineno, linetext, revision, name,
              traceback_info, traceback_hide, traceback_decorator,
              tbid, get_source_line
    :show-inheritance:
