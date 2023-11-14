FROM python:3.6.1-slim

# Python optimization to run on docker
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONIOENCODING UTF-8

RUN echo "deb http://archive.debian.org/debian stretch main" > /etc/apt/sources.list

# Maybe run upgrade as well???
RUN apt-get update

# Requirements
COPY requirements.apt .
RUN xargs apt install -y < requirements.apt

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# User, home, and app basics
RUN useradd --create-home app
WORKDIR /home/app
USER app

COPY . .

ARG build_info
RUN echo ${build_info} > build_info.txt


ENTRYPOINT [ "./gunicorn.sh" ]

# gunicorn --bind 0.0.0.0:$PORT --worker-class gevent --workers $WORKERS --log-file - host_provider.main:app
