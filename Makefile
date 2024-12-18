PWD = $(shell pwd)

LOCAL_DIR = $(PWD)/venv/bin
PYTHON = $(LOCAL_DIR)/python
PYTHON3 = python3.10

args=
# if dockerfile is not defined
ifndef dockerfile
	dockerfile=compose.yml
endif
docker-compose-files=-f ${dockerfile}

up:  ## start docker containers
	docker compose ${docker-compose-files} up -d ${args}

down:  ## stop docker containers
	docker compose ${docker-compose-files} down
stop:  ## stop docker containers
	docker compose ${docker-compose-files} stop

help:  ## Show help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m\033[0m\n"} /^[$$()% a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

sync-requirements: ## Update the local virtual environment with the latest requirements.
	$(PYTHON) -m pip install -r requirements.txt