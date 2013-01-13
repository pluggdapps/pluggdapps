setup :
	@rm -rf pa-env
	@echo "Setting up virtual environment for python 3.x ..."
	@virtualenv --python=python3.2 pa-env 
	@bash -c "source pa-env/bin/activate ; easy_install-3.2 pluggdapps"
	@bash -c "source pa-env/bin/activate ; easy_install-3.2 tayra"

pushcode: push-googlecode push-bitbucket push-github 

push-googlecode:
	hg push https://prataprc@code.google.com/p/paenv/

push-bitbucket:
	hg push https://prataprc@bitbucket.org/prataprc/paenv

push-github:
	hg bookmark -f -r default master
	hg push git+ssh://git@github.com:prataprc/paenv.git
