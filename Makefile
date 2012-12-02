APIDOC_EXCLUDE_PATH=$(PWD)/pluggdapps/scaffolds/*/ \
					$(PWD)/pluggdapps/tests/ \
					$(PWD)/pluggdapps/confs/

SPHINXDOC_OPTIONS=-f -d 1

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

sphinx-doc :
	cp README.rst sphinxdoc/source/
	cp CHANGELOG.rst sphinxdoc/source/
	make -C sphinxdoc html


upload :
	python ./setup.py sdist register -r http://www.python.org/pypi upload -r http://www.python.org/pypi --show-response 
	
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
