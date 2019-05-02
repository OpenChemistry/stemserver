FROM girder/girder:latest-py3

COPY devops/docker/girder/girder.cfg /etc/girder.cfg

# Copy over mongochemserver
COPY ./girder /stem_plugin

RUN pip  install /stem_plugin

# Build client, useful for dev
RUN girder build
