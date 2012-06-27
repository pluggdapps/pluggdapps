develop :
	@rm -rf pa-env
	@echo "Setting up virtual environment for python 3.x ..."
	@virtualenv --python=python3.2 --no-site-packages pa-env 
	@bash -c "source pa-env/bin/activate ; python ./setup.py develop"

bdist_egg : copy
	python ./setup.py bdist_egg

sdist : copy
	python ./setup.py sdist

upload : copy
	python ./setup.py sdist register -r http://www.python.org/pypi upload -r http://www.python.org/pypi --show-response 
	
copy :
	cp CHANGELOG docs/CHANGELOG
	cp LICENSE docs/LICENSE
	cp README docs/README
	cp ROADMAP docs/ROADMAP

cleanall : clean
	rm -rf pa-env

clean :
	rm -rf `find ./ -name "*.pyc"`;
	rm -rf build;
	rm -rf dist;
	rm -rf pluggdapps.egg-info;
	rm -rf pluggdapps.egg-info/;
	rm -rf apps.log
