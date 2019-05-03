FROM python:3.6-slim

COPY flask /server

RUN cd /server && pip install .

ENTRYPOINT ["python", "/server/server.py"]
