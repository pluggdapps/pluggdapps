# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import re
from   setuptools import setup, find_packages
from   os.path    import abspath, dirname, join

here = abspath( dirname(__file__) )
try :
    LONG_DESCRIPTION = open( join( here, 'README.rst' )).read(
                           ).replace(':class:`', '`'
                                    ).replace(':mod:`', '`'
                                             ).replace(':meth:`', '`')
except :
    LONG_DESCRIPTION = ''

version = re.compile( 
            r".*__version__[ ]*=[ ]*'(.*?)'",
            re.S 
          ).match( 
            open( join( here, 'pluggdapps', '__init__.py' )).read()).group(1)

description='Pluggdapps component system, web framework'

classifiers = [
'Development Status :: 4 - Beta',
'Environment :: Plugins',
'Environment :: Web Environment',
'Intended Audience :: Developers',
'Operating System :: POSIX',
'Programming Language :: Python :: 3',
'Topic :: Internet :: WWW/HTTP',
'Topic :: Software Development',
]

setup(
    name='pluggdapps',
    version=version,
    py_modules=[],
    package_dir={},
    packages=find_packages(),
    ext_modules=[],
    scripts=[],
    data_files=[],
    package_data={},                        # setuptools / distutils
    include_package_data=True,              # setuptools
    exclude_package_data={},                # setuptools
    zip_safe=False,                         # setuptools
    entry_points={                          # setuptools
        'console_scripts' : [
           'pa = pluggdapps.pa:main',
        ],
        'pluggdapps' : [
            'package=pluggdapps:package',
        ]
    },
    install_requires=[                      # setuptools
        'tayra>=0.43dev',
        'tayrakit>=0.2dev',
    ],
    extras_require={},                      # setuptools
    setup_requires={},                      # setuptools
    dependency_links=[],                    # setuptools
    namespace_packages=[],                  # setuptools
    test_suite='',                          # setuptools

    provides=[ 'pluggdapps', ],
    requires='',
    obsoletes='',

    author='prataprc',
    author_email='prataprc@gmail.com',
    maintainer='prataprc',
    maintainer_email='prataprc@gmail.com',
    url='http://pythonhosted.org/pluggdapps/',
    download_url='',
    license='General Public License',
    description=description,
    long_description=LONG_DESCRIPTION,
    platforms='',
    classifiers=classifiers,
    keywords=[ 'plugin', 'component', 'web', 'plugin', 'configuration' ],
)
