FROM girder/girder:latest-py3

COPY devops/docker/girder/girder.cfg /etc/girder.cfg

# Copy over mongochemserver
COPY ./girder /stem_plugin

RUN pip  install /stem_plugin

RUN git clone https://github.com/Kitware/cumulus.git /cumulus && \
  pip install --no-cache-dir -r /cumulus/requirements.txt && \
  pip install --no-cache-dir -e /cumulus/girder/newt

# Build client, useful for dev
RUN girder build
