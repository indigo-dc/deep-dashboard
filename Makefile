VIRTUALENV ?= virtualenv
PROJECT = deep_dashboard

ifdef CONFIG_FILE
	OPTS += --config-file `realpath $(CONFIG_FILE)`
endif

ifdef COMPOSE_LOCAL_ENV
	COMPOSE_OPTS += --env-file `realpath $(COMPOSE_LOCAL_ENV)`
endif

ifndef VERBOSE
.SILENT:
endif

.PHONY: help
help:
	@echo 'Makefile to run and test the DEEP Dashboard.                           '
	@echo '                                                                       '
	@echo 'Usage:                                                                 '
	@echo '   make setup      create a virtualenv and install the project inside  '
	@echo '   make develop    create a virtualenv and install the project inside  '
	@echo '	                  in develop mode (i.e. pip install -e )              '
	@echo '   make run        execute the DEEP Dashboard from the virtualenv      '
	@echo '   make regenerate regenerate the virtualenv                           '
	@echo '   make clean      cleanup the existing virtualenv                     '
	@echo '                                                                       '
	@echo 'Docker usage:                                                          '
	@echo '   make docker-build   Build a Docker container image (deep-dashboard) '
	@echo '   make docker-rebuild Force a rebuild of the  Docker container image  '
	@echo '   make docker-run     Run the Docker container,  serve the dashboard  '
	@echo '                                                                       '
	@echo 'Environment variables:                                                 '
	@echo '   VIRTUALENV: path for the virtualenv (defaults to "virtualenv")      '
	@echo '   CONFIG_FILE: path for the configuration file to use (you must set   '
	@echo '                one!!)                                                 '
	@echo '   OPTS: additional options to be pased to the application             '
	@echo '   COMPOSE_LOCAL_ENV: local environment to pass to the Docker compose  '

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
	@echo 'D> Running DEEP Dashboard inside $(VIRTUALENV)'
	. $(VIRTUALENV)/bin/activate; deep-dashboard --listen-ip 127.0.0.1 --listen-port 8080 $(OPTS)

.PHONY: docker-compose-rebuild
docker-compose-rebuild:
	@echo 'D> Building DEEP Dashboard container'
	docker-compose -f docker/docker-compose.yml $(COMPOSE_OPTS) build --no-cache

.PHONY: docker-compose-build
docker-compose-build:
	@echo 'D> Building DEEP Dashboard container'
	docker-compose -f docker/docker-compose.yml $(COMPOSE_OPTS) build

.PHONY: docker-compose-run
docker-compose-run:
	docker-compose -f docker/docker-compose.yml --compatibility $(COMPOSE_OPTS) up --force-recreate
