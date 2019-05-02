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

    def _get_file(self, stem_image_id, user):
        """Get a file object of the stem image"""
        stem_image = self.load(stem_image_id, user=user, level=AccessType.READ)

        if not stem_image:
            raise RestException('StemImage not found.', 404)

        girder_file = FileModel().load(stem_image['fileId'],
                                       level=AccessType.READ, user=user)
        return FileModel().open(girder_file)

    def _get_h5_dataset(self, id, user, path, format='bytes'):
        f = self._get_file(id, user)

        if format == 'bytes':
            return self._get_h5_dataset_bytes(f, path)
        elif format == 'msgpack':
            return self._get_h5_dataset_msgpack(f, path)
        else:
            raise RestException('Unknown format: ' + format)

    def bright(self, id, user, format):
        return self._get_h5_dataset(id, user, '/stem/bright', format)

    def dark(self, id, user, format):
        return self._get_h5_dataset(id, user, '/stem/dark', format)

    def _get_h5_dataset_shape(self, id, user, path):
        f = self._get_file(id, user)
        with h5py.File(f, 'r') as f:
            return f[path].shape

    def bright_shape(self, id, user):
        return self._get_h5_dataset_shape(id, user, '/stem/bright')

    def dark_shape(self, id, user):
        return self._get_h5_dataset_shape(id, user, '/stem/dark')

    def frame(self, id, user, scan_position):
        f = self._get_file(id, user)
        path = '/electron_events/frames'

        # Make sure the scan position is not out of bounds
        with h5py.File(f, 'r') as rf:
            dataset = rf[path]
            if dataset.shape[0] <= 0:
                raise RestException('No data found in dataset: ' + path)
            if scan_position >= dataset.shape[0]:
                msg = ('scan_position ' + str(scan_position) + ' is greater '
                       'than the max: ' + str(dataset.shape[0] - 1))
                raise RestException(msg)

        setResponseHeader('Content-Type', 'application/octet-stream')

        def _stream():
            nonlocal f
            with h5py.File(f, 'r') as rf:
                dataset = rf[path]
                data = dataset[scan_position]
                yield data.tobytes()

        return _stream

    def all_frames(self, id, user):
        f = self._get_file(id, user)
        path = '/electron_events/frames'

        setResponseHeader('Content-Type', 'application/octet-stream')

        def _stream():
            nonlocal f
            with h5py.File(f, 'r') as rf:
                arrays = rf[path][()].tolist()
                for i, array in enumerate(arrays):
                    arrays[i] = array.tolist()

                yield msgpack.packb(arrays, use_bin_type=True)

        return _stream

    def detector_dimensions(self, id, user):
        f = self._get_file(id, user)
        path = '/electron_events/frames'
        with h5py.File(f, 'r') as rf:
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

    def _get_h5_dataset_bytes(self, f, path):
        """Get a dataset as bytes.

        Args:
            f: a file path or file object to an h5 file
            path: a path in the h5 file to a dataset

        Returns: a dataset in bytes
        """
        setResponseHeader('Content-Type', 'application/octet-stream')

        def _stream():
            nonlocal f
            with h5py.File(f, 'r') as f:
                dataset = f[path]
                read_size = 10
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
                    yield array.tobytes()

        return _stream

    def _get_h5_dataset_msgpack(self, f, path):
        """Get a dataset packed with msgpack.

        Args:
            f: a file path or file object to an h5 file
            path: a path in the h5 file to a dataset

        Returns: a dataset packed with msgpack
        """
        with h5py.File(f, 'r') as rf:
            return msgpack.packb(rf[path][()].tolist(), use_bin_type=True)
