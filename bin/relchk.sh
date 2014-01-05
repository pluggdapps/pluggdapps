#! /bin/bash

# This script clones a fresh copy of `paenv` repository from github, installs
# the latest pluggdapps and related packages, like tayra, pagd, from pypi and
# run few tests to check whether the release is broken or not. 

# $ relchk download
# $ relchk
# $ relchk pypi

DEV=$HOME/devgit
ROOT=/tmp/pachk
EGGCACHE=/tmp/egg-cache

echo "Cleaning up $ROOT ..."
rm -rf $ROOT
mkdir -p $ROOT

do_paenv_clone() {
    echo "Fetching fresh clone of paenv from github ..."
    cd $ROOT
    git clone git@github.com:prataprc/paenv.git paenv
    cd paenv
}

do_virtual() {
    echo "Setting up virtual environment for python 3.x ..."
    cd $ROOT/paenv
    virtualenv-$1 --python=python$1 pa-env
    . pa-env/bin/activate
}

test_tayra() {
    echo `which tayra`
    echo "Testing tayra ..."
    tayra -t ok
}

test_pluggdapps() {
    echo `which pa`
    echo "Launching the pa-server ..."
    cd $DEV/paenv-dev
    pa -m -w -c etc/master.ini serve -r
}

test_pagd() {
    echo `which pagd`
    echo "Testing pagd ..."
    mkdir -p $ROOT/myblog
    git clone $HOME/devgit/prataprc.github.io $ROOT/myblog
    cd $ROOT/myblog
    pagd gen
    chromium-browser $ROOT/myblog/index.html&
    cd -
}

if [[ $1 = "download" ]] ; then
    rm -rf $EGGCACHE
    mkdir -p $EGGCACHE
    pip install -d $EGGCACHE beautifulsoup4 markdown docutils
    pip install -d $EGGCACHE lxml pygments mako ply jinja2==2.6
elif [[ $1 = "pypi" ]] ; then
    do_paenv_clone
    do_virtual 3.3
    echo "Installing from pypi ..."
    pip install --no-index -f file://$EGGCACHE beautifulsoup4 markdown docutils
    pip install --no-index -f file://$EGGCACHE lxml pygments ply mako jinja2 
    pip install pluggdapps tayra tayrakit pagd
    test_tayra
    test_pagd
    # test_pluggdapps
else
    do_paenv_clone
    do_virtual 3.3
    echo "Create pluggdapps source-distribution ..."
    cd $DEV/pluggdapps
    make clean sdist > $ROOT/pluggdapps.sdist
    cp dist/* $EGGCACHE

    echo "Create tayra source-distribution ..."
    cd $DEV/tayra
    make clean sdist > $ROOT/tayra.sdist
    cp dist/* $EGGCACHE


    echo "Create tayrakit source-distribution ..."
    cd $DEV/tayrakit
    make clean sdist > $ROOT/tayrakit.sdist
    cp dist/* $EGGCACHE

    echo "Create pagd source-distribution ..."
    cd $DEV/pagd
    make clean sdist > $ROOT/pagd.sdist
    cp dist/* $EGGCACHE

    # This is important, pip gets screwed up ! (TODO : post this mailing list ?)
    cd $ROOT
    pip install --no-index -f file://$EGGCACHE beautifulsoup4 markdown docutils
    pip install --no-index -f file://$EGGCACHE lxml pygments ply mako jinja2 
    pip install --no-index -f file://$EGGCACHE pagd
    pip install --no-index -f file://$EGGCACHE tayrakit
    test_tayra
    test_pagd
    # test_pluggdapps
fi

