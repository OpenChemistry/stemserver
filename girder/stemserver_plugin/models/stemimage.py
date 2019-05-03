from contextlib import contextmanager
import os

import h5py
import msgpack
import numpy as np

from girder.api.rest import setResponseHeader, RestException
from girder.constants import AccessType, AssetstoreType
from girder.models.assetstore import Assetstore as AssetstoreModel
from girder.models.file import File as FileModel
from girder.models.folder import Folder as FolderModel
from girder.models.item import Item as ItemModel
from girder.models.model_base import AccessControlledModel
from girder.utility.filesystem_assetstore_adapter import (
    FilesystemAssetstoreAdapter
)


class StemImage(AccessControlledModel):

    IMPORT_FOLDER = 'stem_images'

    def __init__(self):
        super(StemImage, self).__init__()

    def initialize(self):
        self.name = 'stemimages'
        self.ensureIndices(('fileId',))
        self.exposeFields(level=AccessType.READ, fields=('_id', 'fileId'))

    def filter(self, stem_image, user):
        stem_image = super(StemImage, self).filter(doc=stem_image, user=user)

        del stem_image['_accessLevel']
        del stem_image['_modelType']

        return stem_image

    def validate(self, doc):
        # Ensure the file exists
        if 'fileId' in doc:
            FileModel().load(doc['fileId'], level=AccessType.READ, force=True)
        else:
            raise RestException('stem image must contain `fileId`')

        return doc

    def create(self, user, file_id=None, file_path=None, public=False):
        stem_image = {}
        if file_id:
            stem_image['fileId'] = file_id
        elif file_path:
            # Only admin users can do this
            admin = user.get('admin', False)
            if admin is not True:
                raise RestException('Only admin users can use a filePath', 403)

            name = os.path.basename(file_path)
            item = self._create_import_item(user, name)
            assetstore = self._get_assetstore()

            adapter = FilesystemAssetstoreAdapter(assetstore)
            f = adapter.importFile(item, file_path, user)
            stem_image['fileId'] = f['_id']
        else:
            raise RestException('Must set either fileId or filePath')

        self.setUserAccess(stem_image, user=user, level=AccessType.ADMIN)
        if public:
            self.setPublic(stem_image, True)

        return self.save(stem_image)

    def delete(self, id, user):
        stem_image = self.load(id, user=user, level=AccessType.WRITE)

        if not stem_image:
            raise RestException('StemImage not found.', 404)

        # Try to load the file and check if it was imported.
        # If it was imported, delete the item containing the file.
        # If loading/removing the file fails, remove the stem image anyways
        try:
            f = FileModel().load(stem_image['fileId'], level=AccessType.WRITE,
                                 user=user)
            if f.get('imported', False) is True:
                item = ItemModel().load(f['itemId'], level=AccessType.WRITE,
                                        user=user)
                if item['folderId'] == self._get_import_folder(user)['_id']:
                    ItemModel().remove(item)
        except:
            pass

        return self.remove(stem_image)

    @contextmanager
    def _open_h5py_file(self, stem_image_id, user):
        """Get an h5py file object of the stem image

        This should be used as a context manager as such:

        with self._open_h5py_file(id, user) as f:
            do_stuff_with_file(f)
        """
        stem_image = self.load(stem_image_id, user=user, level=AccessType.READ)

        if not stem_image:
            raise RestException('StemImage not found.', 404)

        girder_file = FileModel().load(stem_image['fileId'],
                                       level=AccessType.READ, user=user)
        with FileModel().open(girder_file) as rf:
            yield h5py.File(rf, 'r')

    def _get_h5_dataset(self, id, user, path, format='bytes'):
        if format == 'bytes' or format is None:
            return self._get_h5_dataset_bytes(id, user, path)
        elif format == 'msgpack':
            return self._get_h5_dataset_msgpack(id, user, path)
        else:
            raise RestException('Unknown format: ' + format)

    def bright(self, id, user, format):
        return self._get_h5_dataset(id, user, '/stem/bright', format)

    def dark(self, id, user, format):
        return self._get_h5_dataset(id, user, '/stem/dark', format)

    def _get_h5_dataset_shape(self, id, user, path):
        with self._open_h5py_file(id, user) as f:
            return f[path].shape

    def bright_shape(self, id, user):
        return self._get_h5_dataset_shape(id, user, '/stem/bright')

    def dark_shape(self, id, user):
        return self._get_h5_dataset_shape(id, user, '/stem/dark')

    def frame(self, id, user, scan_position):
        path = '/electron_events/frames'

        # Make sure the scan position is not out of bounds
        with self._open_h5py_file(id, user) as rf:
            dataset = rf[path]
            if dataset.shape[0] <= 0:
                raise RestException('No data found in dataset: ' + path)
            if scan_position >= dataset.shape[0]:
                msg = ('scan_position ' + str(scan_position) + ' is greater '
                       'than the max: ' + str(dataset.shape[0] - 1))
                raise RestException(msg)

        setResponseHeader('Content-Type', 'application/octet-stream')

        def _stream():
            nonlocal id
            nonlocal user
            with self._open_h5py_file(id, user) as rf:
                dataset = rf[path]
                data = dataset[scan_position]
                yield data.tobytes()

        return _stream

    def all_frames(self, id, user):
        path = '/electron_events/frames'

        setResponseHeader('Content-Type', 'application/octet-stream')

        def _stream():
            nonlocal id
            nonlocal user
            with self._open_h5py_file(id, user) as rf:
                dataset = rf[path]
                for data in self._get_vlen_dataset_in_chunks(dataset):
                    yield msgpack.packb(data, use_bin_type=True)

        return _stream

    def detector_dimensions(self, id, user):
        path = '/electron_events/frames'
        with self._open_h5py_file(id, user) as rf:
            dataset = rf[path]
            if 'Nx' not in dataset.attrs or 'Ny' not in dataset.attrs:
                raise RestException('Detector dimensions not found!', 404)

            return int(dataset.attrs['Nx']), int(dataset.attrs['Ny'])

    def scan_positions(self, id, user):
        return self._get_h5_dataset(id, user,
                                    '/electron_events/scan_positions')

    def _get_import_folder(self, user):
        """Get the folder where files will be imported.

        If the folder does not exist, it will be created.
        """
        return FolderModel().createFolder(user, StemImage.IMPORT_FOLDER,
                                          parentType='user', public=False,
                                          creator=user, reuseExisting=True)

    def _create_import_item(self, user, name):
        """Create a new item and put it in the import folder.

        The new item will be returned.
        """
        folder = self._get_import_folder(user)

        return ItemModel().createItem(name, user, folder)

    def _get_assetstore(self):
        """Gets the asset store and ensures it is a file system"""
        assetstore = AssetstoreModel().getCurrent()
        if assetstore['type'] is not AssetstoreType.FILESYSTEM:
            raise RestException('Current assetstore is not a file system!')
        return assetstore

    def _get_h5_dataset_bytes(self, id, user, path):
        """Get a dataset as bytes.

        Args:
            id: The id of the stem image
            user: The user accessing the stem image
            path: a path in the h5 file to a dataset

        Returns: a dataset in bytes
        """
        setResponseHeader('Content-Type', 'application/octet-stream')

        def _stream():
            nonlocal id
            nonlocal user
            with self._open_h5py_file(id, user) as rf:
                dataset = rf[path]
                for array in self._get_dataset_in_chunks(dataset):
                    yield array.tobytes()

        return _stream

    def _get_h5_dataset_msgpack(self, id, user, path):
        """Get a dataset packed with msgpack.

        Args:
            id: The id of the stem image
            user: The user accessing the stem image
            path: a path in the h5 file to a dataset

        Returns: a dataset packed with msgpack
        """
        setResponseHeader('Content-Type', 'application/octet-stream')

        def _stream():
            nonlocal id
            nonlocal user
            with self._open_h5py_file(id, user) as rf:
                dataset = rf[path]
                for array in self._get_dataset_in_chunks(dataset):
                    yield msgpack.packb(array.tolist(), use_bin_type=True)

        return _stream

    def _get_vlen_dataset_in_chunks(self, dataset, max_chunk_size=64000):
        """A generator to yield lists of lists of a vlen dataset.

        A vlen dataset is a dataset whose elements are variable length
        arrays.

        Args:
            dataset: An h5py dataset containing vlen arrays
            max_chunk_size: The maximum size in bytes to be sent. This
                            will be used to determine how many arrays
                            to send. Note that it will always send at
                            least one array, even if the size exceeds
                            the max.
        Yields: Arrays of the dataset
        """
        current_size = 0
        data = []
        for array in dataset:
            array_size = array.size * array.dtype.itemsize
            if len(data) != 0:
                if current_size + array_size > max_chunk_size:
                    yield data
                    data.clear()
                    current_size = 0

            data.append(array.tolist())
            current_size += array_size

        yield data

    def _get_dataset_in_chunks(self, dataset, max_chunk_size=64000):
        """A generator to yield numpy arrays of the dataset.

        Args:
            dataset: An h5py dataset
            max_chunk_size: The maximum size in bytes to be sent. This
                            will be used to determine how many arrays
                            to send. Note that it will always send at
                            least one array, even if the size exceeds
                            the max.
        Yields: Arrays of the dataset
        """
        approx_items_per_array = dataset.size / dataset.shape[0]
        approx_size_per_array = approx_items_per_array * dataset.dtype.itemsize

        read_size = int(max_chunk_size // approx_size_per_array)
        if read_size == 0:
            read_size = 1

        if read_size > dataset.shape[0]:
            read_size = dataset.shape[0]

        total_read = 0
        while total_read != dataset.shape[0]:
            if total_read + read_size > dataset.shape[0]:
                read_size = dataset.shape[0] - total_read

            shape = (read_size,) + dataset.shape[1:]
            array = np.empty(shape, dtype=dataset.dtype)

            start = total_read
            end = start + read_size

            dataset.read_direct(array, source_sel=np.s_[start:end])
            total_read += read_size

            yield array
