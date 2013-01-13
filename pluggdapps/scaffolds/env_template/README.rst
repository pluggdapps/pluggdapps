Clone this repository from github or google-code or bit-bucket, and do,

.. code-block:: bash

   cd paenv
   make setup

This will create a virtual environment and install latest version of
pluggdapps and related packages. A note on the directory structure,

**etc/**

Contains all configuration files. ``etc/master.ini`` is the master 
configuration file and each web-application instance booted under the
pluggdapps environment can have a configuration file. For instance,
``etc/webadmin.ini`` configures ``WebAdmin`` application loaded as
http://localhost/webadmin.

**db/**

Contains database files. Pluggdapps officially depends only on linux,
python-3.x and python standard library. Hence, you can expect that many
applications under pluggdapps will be using ``sqlite3`` for database and they
are configured under this directory.

**Start native HTTP server**

.. code-block:: bash

    ./pa-env/bin/pa -w -c etc/master.ini serve

To learn more about the ``pa`` command try,

.. code-block:: bash

    ./pa-env/bin/pa -h

To learn more about the ``serve`` sub-command try,

.. code-block:: bash

    ./pa-env/bin/pa serve -h
