FROM python:2.7-slim
MAINTAINER Sa Phi
RUN pip install virtualenv

WORKDIR /app
RUN virtualenv /env
ADD requirements.txt /app/requirements.txt
RUN /env/bin/pip install -r requirements.txt
ADD . /app

ENV ADDRESS 'http://172.16.69.240/owncloud/'

EXPOSE 5000

CMD []
ENTRYPOINT ["/env/bin/python", "/app/app.py"]
