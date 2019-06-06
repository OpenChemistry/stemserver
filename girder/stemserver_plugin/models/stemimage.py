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

    ALLOWED_FORMATS = ['bytes', 'msgpack']

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
            item = self._create_import_item(user, name, public)
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

        public = stem_image.get('public', False)

        # Try to load the file and check if it was imported.
        # If it was imported, delete the item containing the file.
        # If loading/removing the file fails, remove the stem image anyways
        try:
            f = FileModel().load(stem_image['fileId'], level=AccessType.WRITE,
                                 user=user)
            if f.get('imported', False) is True:
                item = ItemModel().load(f['itemId'], level=AccessType.WRITE,
                                        user=user)
                if item['folderId'] == self._get_import_folder(user,
                                                               public)['_id']:
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

    def _get_h5_dataset(self, id, user, path, offset=None, limit=None, format='bytes'):
        if format == 'bytes' or format is None:
            return self._get_h5_dataset_bytes(id, user, path, offset, limit)
        elif format == 'msgpack':
            return self._get_h5_dataset_msgpack(id, user, path, offset, limit)
        else:
            raise RestException('Unknown format: ' + format)

    def image_names(self, id, user):
        path = '/stem/images'
        with self._open_h5py_file(id, user) as rf:
            return rf[path].attrs['names'].tolist()

    def image(self, id, user, format, name):
        path = '/stem/images'

        if format is None:
            format = 'bytes'

        if format not in StemImage.ALLOWED_FORMATS:
            raise RestException('Unknown format: ' + format)

        with self._open_h5py_file(id, user) as rf:
            # Check if the name is an integer. If so, assume it is
            # an index and not a name.
            if self._str_is_int(name):
                index = int(name)
                if index >= len(rf[path]):
                    raise RestException('Index is too large')
            else:
                # Get the index of the data from the name
                index = self._get_image_index_from_name(rf[path], name)

        setResponseHeader('Content-Type', 'application/octet-stream')
        def _stream():
            with self._open_h5py_file(id, user) as rf:
                dataset = rf[path][index]
                for array in self._get_vlen_dataset_in_chunks(dataset):
                    if format == 'bytes':
                        yield np.array(array, copy=False).tobytes()
                    elif format == 'msgpack':
                        yield msgpack.packb(array, use_bin_type=True)

        return _stream

    def image_shape(self, id, user, name):
        path = '/stem/images'
        with self._open_h5py_file(id, user) as rf:
            dataset = rf[path]

            if self._str_is_int(name):
                index = int(name)
                if index >= len(dataset):
                    raise RestException('Index is too large')
            else:
                index = self._get_image_index_from_name(dataset, name)

            return dataset[index].shape

    def frame(self, id, user, scan_position, type, format):
        path = self._get_path_to_type(type)

        # Make sure the scan position is not out of bounds
        with self._open_h5py_file(id, user) as rf:
            dataset = rf[path]
            if dataset.shape[0] <= 0:
                raise RestException('No data found in dataset: ' + path)
            if scan_position >= dataset.shape[0]:
                msg = ('scan_position ' + str(scan_position) + ' is greater '
                       'than the max: ' + str(dataset.shape[0] - 1))
                raise RestException(msg)

        return self._get_h5_dataset(id, user, path, offset=scan_position, limit=1, format=format)

    def all_frames(self, id, user, type, limit=None, offset=None):
        path = self._get_path_to_type(type)

        # Ensure limit and offset are reasonable
        with self._open_h5py_file(id, user) as rf:
            limit, offset = self._check_limit_and_offset(rf[path], limit,
                                                         offset)

        setResponseHeader('Content-Type', 'application/octet-stream')

        def _stream():
            nonlocal id
            nonlocal user
            with self._open_h5py_file(id, user) as rf:
                dataset = rf[path]
                for data in self._get_vlen_dataset_in_chunks(dataset, limit,
                                                             offset):
                    yield msgpack.packb(data, use_bin_type=True)

        return _stream

    def frame_shape(self, id, user, type):
        path = self._get_path_to_type(type)
        with self._open_h5py_file(id, user) as rf:
            dataset = rf[path]
            if type == 'electron':
                if 'Nx' not in dataset.attrs or 'Ny' not in dataset.attrs:
                    raise RestException('Detector dimensions not found!', 404)

                return int(dataset.attrs['Nx']), int(dataset.attrs['Ny'])
            elif type == 'raw':
                return dataset.shape[1], dataset.shape[2]

        raise RestException('In frame_shape, unknown type: ' + type)

    def scan_positions(self, id, user, type):
        path = self._get_path_to_type(type)
        if type == 'electron':
            return self._get_h5_dataset(id, user, path)
        elif type == 'raw':
            setResponseHeader('Content-Type', 'application/octet-stream')

            def _stream():
                with self._open_h5py_file(id, user) as rf:
                    dataset = rf[path]
                    array = np.array([i for i in range(dataset.shape[0])])
                    yield array.tobytes()

            return _stream

        raise RestException('In scan_positions, unknown type: ' + type)

    def _get_import_folder(self, user, public=False):
        """Get the folder where files will be imported.

        If the folder does not exist, it will be created.
        """
        root_folder = FolderModel().createFolder(user, StemImage.IMPORT_FOLDER,
                                                 parentType='user',
                                                 public=False,
                                                 creator=user,
                                                 reuseExisting=True)

        if public:
            name = 'Public'
        else:
            name = 'Private'

        return FolderModel().createFolder(root_folder, name, public=public,
                                          creator=user, reuseExisting=True)

    def _create_import_item(self, user, name, public=False):
        """Create a new item and put it in the import folder.

        The new item will be returned.
        """
        folder = self._get_import_folder(user, public)

        return ItemModel().createItem(name, user, folder)

    def _get_assetstore(self):
        """Gets the asset store and ensures it is a file system"""
        assetstore = AssetstoreModel().getCurrent()
        if assetstore['type'] is not AssetstoreType.FILESYSTEM:
            raise RestException('Current assetstore is not a file system!')
        return assetstore

    def _get_h5_dataset_bytes(self, id, user, path, offset=None, limit=None):
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
                for array in self._get_dataset_in_chunks(dataset, offset, limit):
                    yield array.tobytes()

        return _stream

    def _get_h5_dataset_msgpack(self, id, user, path, offset=None, limit=None):
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
                for array in self._get_dataset_in_chunks(dataset, offset, limit):
                    yield msgpack.packb(array.tolist(), use_bin_type=True)

        return _stream

    def _get_vlen_dataset_in_chunks(self, dataset, limit=1e6, offset=0,
                                    max_chunk_size=64000):
        """A generator to yield lists of lists of a vlen dataset.

        A vlen dataset is a dataset whose elements are variable length
        arrays.

        This will also work if `dataset` is a numpy array.

        Args:
            dataset: An h5py dataset containing vlen arrays
            limit: Limit the number of arrays to be obtained
            offset: Offset arrays to be obtained
            max_chunk_size: The maximum size in bytes to be sent. This
                            will be used to determine how many arrays
                            to send. Note that it will always send at
                            least one array, even if the size exceeds
                            the max.
        Yields: Arrays of the dataset
        """

        num_arrays = min(limit, dataset.shape[0])

        current_size = 0
        data = []
        for i in range(num_arrays):
            array = dataset[offset + i]
            array_size = array.size * array.dtype.itemsize
            if len(data) != 0:
                if current_size + array_size > max_chunk_size:
                    yield data
                    data.clear()
                    current_size = 0

            data.append(array.tolist())
            current_size += array_size

        yield data

    def _get_dataset_in_chunks(self, dataset, offset=None, limit=1e6, max_chunk_size=64000):
        """A generator to yield numpy arrays of the dataset.

        Args:
            dataset: An h5py dataset
            limit: Limit the number of arrays to be obtained
            offset: Offset arrays to be obtained
            max_chunk_size: The maximum size in bytes to be sent. This
                            will be used to determine how many arrays
                            to send. Note that it will always send at
                            least one array, even if the size exceeds
                            the max.
        Yields: Arrays of the dataset
        """
        num_arrays = min(limit, dataset.shape[0])

        current_size = 0
        start = 0

        def is_ref_type(dataset):
            return dataset.dtype.kind == 'O'

        def get_chunk_shape(start, stop, dataset):
            if stop - start == 1:
                # If the one dataset is a reference, follow the reference to get the shape
                if is_ref_type(dataset):
                    return dataset[start].shape
                else:
                    return dataset.shape[1:]
            else:
                return (stop - start,) + dataset.shape[1:]

        def get_chunk_data(start, stop, dataset):
            if stop - start == 1 and is_ref_type(dataset):
                return dataset[start]

            shape = get_chunk_shape(start, stop, dataset)
            dtype = dataset.dtype
            array = np.empty(shape, dtype=dtype)
            dataset.read_direct(array, source_sel=np.s_[start:stop])
            return array

        for i in range(num_arrays):
            array_size = dataset[offset + i].size * dataset.dtype.itemsize
            if current_size != 0:
                if current_size + array_size > max_chunk_size:
                    yield get_chunk_data(offset + start, offset + i, dataset)
                    current_size = 0
                    start = i

            current_size += array_size

        stop = num_arrays
        yield get_chunk_data(offset + start, offset + stop, dataset)

    def _get_path_to_type(self, type):
        """Get the path to the dataset for the given type"""
        if type == 'electron':
            return '/electron_events/frames'
        elif type == 'raw':
            return '/frames'
        raise RestException('Unknown type: ' + type)

    def _check_limit_and_offset(self, dataset, limit, offset):
        """Check that the limit and offset are reasonable

        This function does sanity checks and raises an exception if
        an issue is found.

        This function also returns the limit and offset as integers (and
        modifies them if they were set to `None`).
        """

        if limit is None:
            limit = dataset.shape[0]

        if offset is None:
            offset = 0

        if int(offset) < 0:
            raise RestException('Offset cannot be less than zero')

        if int(offset) >= dataset.shape[0]:
            msg = ('Offset is out of bounds (cannot be ' +
                   str(dataset.shape[0]) + ' or greater)')
            raise RestException(msg)

        if int(limit) <= 0:
            raise RestException('Limit cannot be less than one')

        return int(limit), int(offset)

    def _get_image_index_from_name(self, dataset, name):
        """Get the index of an image from a name.

        This assumes that dataset.shape[0] is the index for the images,
        and that the dataset has a `names` attribute that contains the
        names of the images.
        """
        try:
            return dataset.attrs['names'].tolist().index(name)
        except ValueError:
            raise RestException(name + ' is not in ' + dataset.name)

    def _str_is_int(self, s):
        """A simple function to check if a string is an int"""
        try:
            int(s)
            return True
        except ValueError:
            return False
