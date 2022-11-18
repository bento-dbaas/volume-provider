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

docker_deploy_build: 
	@echo "tag usada:${TAG}"
	@echo "exemplo de uso make docker_deploy_build TAG=v1.02"
	docker build . -t us-east1-docker.pkg.dev/gglobo-dbaas-hub/dbaas-docker-images/volume-provider:${TAG}

docker_deploy_push:
	@echo "tag usada:${TAG}"
	@echo "exemplo de uso make docker_deploy_push TAG=v1.02"
	docker push us-east1-docker.pkg.dev/gglobo-dbaas-hub/dbaas-docker-images/volume-provider:${TAG}