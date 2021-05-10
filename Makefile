VIRTUALENV ?= virtualenv
PROJECT = deep_dashboard

ifdef CONFIG_FILE
	OPTS = --config-file $(CONFIG_FILE)
endif

ifndef VERBOSE
.SILENT:
endif

.PHONY: help
help:
	@echo 'Makefile to run and test the DEEPaaS API                               '
	@echo '                                                                       '
	@echo 'Usage:                                                                 '
	@echo '   make setup      generate a virtualenv and install the project inside it '
	@echo '   make develop    generate a virtualenv and install the project inside it '
	@echo '	                  in develop mode (i.e. pip install -e )              '
	@echo '   make run        execute the API service from the virtualenv         '
	@echo '   make regenerate regenerate the virtualenv                           '
	@echo '   make clean      cleanup the existing virtualenv                     '
	@echo '                                                                       '
	@echo 'Environment variables:                                                 '
	@echo '	VIRTUALENV: path for the virtualenv (defaults to "virtualenv")        '

.PHONY: setup
setup: $(VIRTUALENV) 
	. $(VIRTUALENV)/bin/activate; cd $(VIRTUALENV); pip uninstall -y $(PROJECT)
	. $(VIRTUALENV)/bin/activate; pip install .

.PHONY: develop
develop: $(VIRTUALENV) 
	. $(VIRTUALENV)/bin/activate; cd $(VIRTUALENV); pip uninstall -y $(PROJECT)
	. $(VIRTUALENV)/bin/activate; pip install -e .

#.PHONY: develop
#develop: requirements.txt virtualenv install
#
regenerate: | clean $(VIRTUALENV)

$(VIRTUALENV): requirements.txt
	@echo 'D> Creating $(VIRTUALENV)...'
	virtualenv --python=python3 $(VIRTUALENV)
	. $(VIRTUALENV)/bin/activate; pip install -r requirements.txt

.PHONY: clean 
clean:
	@echo 'D> Deleting $(VIRTUALENV)...'
	rm -rf $(VIRTUALENV)

.PHONY: run 
run: setup $(VIRTUALENV)
	@echo 'D> Running DEEPaaS inside $(VIRTUALENV)'
	. $(VIRTUALENV)/bin/activate; deep-dashboard --listen-ip 127.0.0.1 --listen-port 8080 $(OPTS)
