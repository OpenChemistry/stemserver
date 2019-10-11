FROM openchemistry/stempy

# Build HDF5 with parallel support
RUN cd /source && \
  wget https://s3.amazonaws.com/hdf-wordpress-1/wp-content/uploads/manual/HDF5/HDF5_1_10_5/source/hdf5-1.10.5.tar.gz && \
  tar xvf hdf5-1.10.5.tar.gz

RUN mkdir -p /build/hdf5-1.10.5 && \
   cd /build/hdf5-1.10.5 && \
   cmake \
   -DBUILD_TESTING:BOOL=OFF \
   -DHDF5_BUILD_CPP_LIB:BOOL=OFF \
   -DHDF5_ENABLE_PARALLEL:BOOL=ON \
   -DCMAKE_BUILD_TYPE:STRING=Release \
   /source/hdf5-1.10.5 && \
   make -j4 install

# Uninstall h5py so we can replace with a parallel enable version.
RUN pip3 uninstall -y h5py

RUN cd /build && wget https://github.com/h5py/h5py/releases/download/2.10.0/h5py-2.10.0.tar.gz && \
   tar xvf h5py-2.10.0.tar.gz && cd /build/h5py-2.10.0 && \
   export CC=mpicc && \
   python3 setup.py configure --mpi --hdf5=/usr/local/HDF_Group/HDF5/1.10.5 && \
   python3 setup.py build && \
   python3 setup.py install

COPY worker /worker

RUN pip3 install /worker && \
    rm -rf /worker

ENTRYPOINT ["stemworker"]
