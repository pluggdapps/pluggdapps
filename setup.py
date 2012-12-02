# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 Netscale Computing

import re
from   setuptools import setup, find_packages
from   os.path    import abspath, dirname, join

here = abspath( dirname(__file__) )
LONG_DESCRIPTION = open( join( here, 'README.rst' )).read(
                       ).replace(':class:`', '`'
                                ).replace(':mod:`', '`'
                                         ).replace(':meth:`', '`')

version = re.compile( 
            r".*__version__[ ]*=[ ]*'(.*?)'",
            re.S 
          ).match( 
            open( join( here, 'pluggdapps', '__init__.py' )).read()).group(1)

description='Pluggdapps component architecture, web framework'

classifiers = [
'Development Status :: 4 - Beta',
'Environment :: Web Environment',
'Intended Audience :: Developers',
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
    entry_points = """\
    [pluggdapps]
      package=pluggdapps:package
    """,
    install_requires=[                      # setuptools
    ],
    extras_require={},                      # setuptools
    setup_requires={},                      # setuptools
    dependency_links=[],                    # setuptools
    namespace_packages=[],                  # setuptools
    test_suite='',                          # setuptools

    provides=[ 'pluggdapps', ],
    requires='',
    obsoletes='',

    author='R Pratap Chakravarthy',
    author_email='prataprc@gmail.com',
    maintainer='R Pratap Chakravarthy',
    maintainer_email='prataprc@gmail.com',
    url='http://pluggdapps.com',
    download_url='',
    license='General Public License',
    description=description,
    long_description=LONG_DESCRIPTION,
    platforms='',
    classifiers=classifiers,
    keywords=[ 'plugin', 'component', 'architecture', 'web' ],
)
