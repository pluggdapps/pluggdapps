APIDOC_EXCLUDE_PATH=$(PWD)/pluggdapps/scaffolds/*/ \
					$(PWD)/pluggdapps/tests/ \
					$(PWD)/pluggdapps/confs/

SPHINXDOC_OPTIONS=-f -d 1

.PHONY: develop bdist_egg sdist sphinx-compile sphinx upload pushcode \
		push-googlecode push-bitbucket push-github cleanall clean

develop :
	@rm -rf pa-env
	@echo "Setting up virtual environment for python 3.x ..."
	@virtualenv --python=python3.2 pa-env 
	@bash -c "source pa-env/bin/activate ; python ./setup.py develop"
	@bash -c "source pa-env/bin/activate ; easy_install-3.2 sphinx"

bdist_egg :
	python ./setup.py bdist_egg

sdist :
	python ./setup.py sdist

sphinx-compile :
	cp README.rst sphinxdoc/source/index.rst
	cat sphinxdoc/source/index.rst.inc >> sphinxdoc/source/index.rst
	cp CHANGELOG.rst sphinxdoc/source/
	cp docs/glossary.rst sphinxdoc/source/
	rm -rf sphinxdoc/build/html/
	make -C sphinxdoc html

sphinx : sphinx-compile
	cd sphinxdoc/build/html; zip -r pluggdapps.sphinxdoc.zip ./

upload :
	python ./setup.py sdist register -r http://www.python.org/pypi upload -r http://www.python.org/pypi
	
pushcode: push-googlecode push-bitbucket push-github 

push-googlecode:
	hg push https://prataprc@code.google.com/p/pluggdapps/

push-bitbucket:
	hg push https://prataprc@bitbucket.org/prataprc/pluggdapps

push-github:
	hg bookmark -f -r default master
	hg push git+ssh://git@github.com:prataprc/pluggdapps.git

cleanall : clean cleandoc
	rm -rf pa-env

cleandoc :
	rm -rf sphinxdoc/build/*

clean :
	rm -rf `find ./ -name "*.pyc"`;
	rm -rf build;
	rm -rf dist;
	rm -rf pluggdapps.egg-info;
	rm -rf pluggdapps.egg-info/;
	rm -rf apps.log
