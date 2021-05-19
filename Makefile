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
