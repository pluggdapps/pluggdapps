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
	@bash -c "source pa-env/bin/activate ; pip install sphinx"

bdist_egg :
	python ./setup.py bdist_egg

sdist :
	python ./setup.py sdist

sphinx-compile :
	mkdir -p docs/_build
	pa -w confdoc -p pluggdapps -o docs/configuration.rst
	cp CHANGELOG.rst docs/
	cp README.rst docs/index.rst
	cat docs/index.rst.inc >> docs/index.rst
	rm -rf docs/_build/html/
	make -C docs html

sphinx : sphinx-compile
	cd docs/_build/html; zip -r pluggdapps.sphinxdoc.zip ./

upload :
	python ./setup.py sdist register -r http://www.python.org/pypi upload -r http://www.python.org/pypi
	
pushcode: push-googlecode push-github push-bitbucket 

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
	rm -rf docs/_build/*

clean :
	rm -rf `find ./ -name "*.pyc"`;
	rm -rf docs/_build;
	rm -rf dist;
	rm -rf pluggdapps.egg-info;
	rm -rf pluggdapps.egg-info/;
	rm -rf apps.log
