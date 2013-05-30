#! /bin/bash

# This script clones a fresh copy of `paenv` repository from github, installs
# the latest pluggdapps and related packages, like tayra, pagd, from pypi and
# run few tests to check whether the release is broken or not. 

echo "Cleaning up /tmp/pachk ..."
DEV=$HOME/dev
rm -rf /tmp/pachk
mkdir -p /tmp/pachk

echo "Fetching fresh clone of paenv from github ..."
cd /tmp/pachk
git clone git@github.com:prataprc/paenv.git paenv
cd paenv

echo "Setting up virtual environment for python 3.x ..."
virtualenv-3.2 --python=python3.2 pa-env 
. pa-env/bin/activate

echo "beautifulsoup4"
pip install beautifulsoup4

if [[ $1 = "pypi" ]] ; then
    echo "Installing from pypi ..."
    pip install pluggdapps tayra tayrakit
else
    echo "Create pluggdapps source-distribution ..."
    cd $DEV/netscale/pluggdapps
    make clean sdist > /tmp/pachk/pluggdapps.sdist
    pip install $DEV/netscale/pluggdapps/dist/*.tar.gz

    echo "Create tayra source-distribution ..."
    cd $DEV/tayra
    make clean sdist > /tmp/pachk/tayra.sdist
    pip install $DEV/tayra/dist/*.tar.gz


    echo "Create tayrakit source-distribution ..."
    cd $DEV/tayrakit
    make clean sdist > /tmp/pachk/tayrakit.sdist
    pip install $DEV/tayrakit/dist/*.tar.gz
fi

echo `which pa`
echo `which tayra`
echo "Testing tayra ..."
tayra -t ok
echo "Launching the pa-server ..."
pa -m -w -c etc/master.ini serve -r
