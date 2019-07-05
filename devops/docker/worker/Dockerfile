FROM openchemistry/stempy

RUN wget https://bootstrap.pypa.io/get-pip.py && \
    python3 get-pip.py

COPY worker /worker

RUN pip install /worker && \
    rm -rf /worker

ENTRYPOINT ["stemworker"]
