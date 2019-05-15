FROM python:3.6-slim

RUN pip install gunicorn

COPY flask /server

RUN cd /server && pip install .

WORKDIR /server

ENTRYPOINT ["gunicorn", "--worker-class", "eventlet",  "-w",  "1",  "server:app", "-b", "127.0.0.1:5000"]
