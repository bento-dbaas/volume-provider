dev:
	export FLASK_DEBUG=1

run:
	export FLASK_APP=./volume_provider/app.py; python -m flask run --host 0.0.0.0

test:
	export DBAAS_AWS_PROXY=;coverage run --source=./ -m unittest discover --start-directory ./volume_provider/tests -p "*.py"

deploy_dev:
	tsuru app-deploy -a volume-provider-dev .

deploy_prod:
	tsuru app-deploy -a volume-provider .
