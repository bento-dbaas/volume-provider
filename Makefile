dev:
	export FLASK_DEBUG=1

run:
	export DBAAS_TEAM_ID=5a550b6b0af460dc4b467836; export FLASK_APP=./volume_provider/app.py; python -m flask run --host 0.0.0.0

test:
	DBAAS_HTTP_PROXY=;DBAAS_HTTPS_PROXY=;coverage run --source=./ -m unittest discover --start-directory ./volume_provider/tests -p "*.py"

shell:
	DBAAS_HTTP_PROXY=;DBAAS_HTTPS_PROXY=;PYTHONPATH=. ipython

test_report: test
	coverage report -m

deploy_dev:
	tsuru app-deploy -a volume-provider-dev .

deploy_prod:
	tsuru app-deploy -a volume-provider .


# Docker part, for deploy
# TODO, standardize with other providers

docker_build:
	GIT_BRANCH=$$(git branch --show-current); \
	GIT_COMMIT=$$(git rev-parse --short HEAD); \
	DATE=$$(date +"%Y-%M-%d_%T"); \
	INFO="date:$$DATE  branch:$$GIT_BRANCH  commit:$$GIT_COMMIT"; \
	docker build -t dbaas/volume_provider --label git-commit=$(git rev-parse --short HEAD) --build-arg build_info="$$INFO" .

docker_run:
	make docker_stop
	docker rm volume_provider
	docker run --name=volume_provider -d -p 80:80 dbaas/volume_provider 

docker_stop:
	docker stop volume_provider

docker_deploy_gcp:
	@echo "tag usada:${TAG}"
	@echo "exemplo de uso:"
	@echo "make docker_deploy_gcp TAG=v1.02"
	make docker_deploy_build TAG=${TAG}
	make docker_deploy_push TAG=${TAG}
	make set_new_tag TAG=${TAG} ENV=${ENV}

docker_deploy_build: 
	@echo "tag usada:${TAG}"
	@echo "exemplo de uso make docker_deploy_build TAG=v1.02"
	GIT_BRANCH=$$(git branch --show-current); \
	GIT_COMMIT=$$(git rev-parse --short HEAD); \
	DATE=$$(date +"%Y-%M-%d_%T"); \
	INFO="date:$$DATE  branch:$$GIT_BRANCH  commit:$$GIT_COMMIT"; \
	docker build . -t us-east1-docker.pkg.dev/gglobo-dbaas-hub/dbaas-docker-images/volume-provider:${TAG} \
		--label git-commit=$(git rev-parse --short HEAD) \
		--build-arg build_info="$$INFO"

docker_deploy_push:
	@echo "tag usada:${TAG}"
	@echo "exemplo de uso make docker_deploy_push TAG=v1.02"
	docker push us-east1-docker.pkg.dev/gglobo-dbaas-hub/dbaas-docker-images/volume-provider:${TAG}

get_last_tag:
	@echo "exemplo de uso make get_last_tag ENV=DEV"; \
	echo "exemplo de uso make get_last_tag ENV=DEV_2"; \
	echo "exemplo de uso make get_last_tag ENV=PROD"; \
	make set_env ENV=${ENV}; \
	SECRET_NAME="DBDEV_${ENV}_VOLUME_PROVIDER_IMAGE_VERSION"; \
	echo "Getting secret $${SECRET_NAME}"; \
	gcloud secrets versions access "latest" --secret "$${SECRET_NAME}"; \
	echo " " 

set_new_tag:
	@echo "tag usada:${TAG}"
	@echo "exemplo de uso make set_tag TAG=v1.02 ENV=DEV"
	@echo "exemplo de uso make set_tag TAG=v1.02 ENV=DEV_2"
	@echo "exemplo de uso make set_tag TAG=v1.034 ENV=PROD"
	@make set_env ENV=${ENV}; \
	if [ $$? -eq 0 ]; then \
		echo "env set"; \
	else \
		echo "ERROR SETTING ENVIRONMENT"; \
		exit 1; \
	fi; \
	SECRET=${TAG}; \
	SECRET_NAME="DBDEV_${ENV}_VOLUME_PROVIDER_IMAGE_VERSION"; \
	echo "$${SECRET_NAME}"; \
	echo "$${SECRET}" | gcloud secrets create "$${SECRET_NAME}" --locations=us-east1,southamerica-east1 --replication-policy="user-managed" --labels="app=dbaas-app" --data-file=- ; \
	if [ $$? -eq 0 ]; then \
		echo "Created the new secret sucessfully"; \
	else \
		echo "Secret already exists, updating its version!" ; \
		echo $${SECRET} | gcloud secrets versions add $${SECRET_NAME} --data-file=- ; \
	fi

set_env:
	@echo "Project env:${ENV}"; \
	if [ "${ENV}" = "DEV" ]; then \
    	echo 'changing project to DEV'; \
    	LOWERCASE_ENV="dev"; \
    	gcloud config set project gglobo-dbaaslab-dev-qa; \
		exit 0; \
    elif [ "${ENV}" = "DEV_2" ]; then \
    	echo 'changing project to DEV_2'; \
    	LOWERCASE_ENV="dev_2"; \
    	gcloud config set project gglobo-dbaaslab-dev-qa; \
		exit 0; \
	elif [ "${ENV}" = "PROD" ]; then \
		echo 'changing project to PROD'; \
		LOWERCASE_ENV="prod"; \
		gcloud config set project gglobo-dbaas-hub; \
		exit 0; \
	else\
		echo "ENV not found. Exiting";\
		echo "please call like this: make set_env ENV=PROD or DEV";\
		exit 1;\
	fi\