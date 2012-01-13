develop :
	rm -rf pluggdapps-env
	virtualenv pluggdapps-env --no-site-packages
	bash -c "source pluggdapps-env/bin/activate ; python ./setup.py develop"

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
	rm -rf pluggdapps-env

clean :
	rm -rf build;
	rm -rf dist;
	rm -rf pluggdapps.egg-info;
	rm -rf pluggdapps.egg-info/;
