Creating a new pluggdapps project
=================================

Pluggdapps uses python3, its stdlib, setuptools and virtual-environment to
create a notion of platform. A platform is an environment, a run-time, using
which developers can create programs and distribute them to other machines as
long as they run the same platform.

Pluggdapps project is packaged using setuptools and while doing so, it is
expected that ``[pluggdapps] package`` entry point is defined, for eg.,

.. code-block:: python

    # setup.py
    ...
    setup(
        ...
        ...
        entry_points={                          # setuptools
            'pluggdapps' : [
                'package=<module.path>:<function-name>',
            ]
        },
        ...
    )

Typically, a pluggdapps project will define the package entry-point function
as ``package``. Presence of this entry point will indicate that the package is
part of pluggdapps platform. This entry point will be called during platform 
startup, and expected to return a dictionay of package information.

**Example package**

Tayra is a templating language that is distributed as pluggdapps package, the
following code is taken from ``tayra/__init__.py`` package file,

.. code-block:: python

    def package( pa ) :
        loadttls( pa, template_plugins )
        return {
            'ttlplugins' : template_plugins,
        }

Note that tayra package is using this entry point to load template plugins and
returns a dictionary of information about the package.

Package information
-------------------

``ttlplugins``,
    List of template files with absolute path names. Presence of this
    key indicates that the package is providing tayra template plugins.
