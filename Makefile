dev:
	export FLASK_DEBUG=1


run:
	export FLASK_APP=./volume_provider/app.py; python -m flask run
