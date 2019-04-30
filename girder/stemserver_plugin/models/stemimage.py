import h5py
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
    IMPORT_ITEM_NAME = '_imported_images'

    def __init__(self):
        super(StemImage, self).__init__()

    def initialize(self):
        self.name = 'stemimages'
        self.ensureIndices(('_id', 'fileId'))
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
            raise RestException('stem image must contain `fileId`', code=400)

        return doc

    def create(self, user, file_id=None, file_path=None, public=False):
        stem_image = {}
        if file_id:
            stem_image['fileId'] = file_id
        elif file_path:
            # Only admin users can do this
            admin = user.get('admin', False)
            if admin is not True:
                raise RestException('Only admin users can use a filePath',
                                    code=403)

            item = self._get_import_stem_item(user)
            name = self._get_import_unique_file_name(item)
            assetstore = self._get_assetstore()

            adapter = FilesystemAssetstoreAdapter(assetstore)
            f = adapter.importFile(item, file_path, user, name)
            stem_image['fileId'] = f['_id']
        else:
            raise RestException('Must set either fileId or filePath',
                                code=400)

        self.setUserAccess(stem_image, user=user, level=AccessType.ADMIN)
        if public:
            self.setPublic(stem_image, True)

        return self.save(stem_image)

    def delete(self, id, user):
        stem_image = self.load(id, user=user, level=AccessType.WRITE)

        if not stem_image:
            raise RestException('StemImage not found.', code=404)

        # Try to load the file and check if it was imported.
        # If it was imported, delete the imported file.
        # If loading the file fails, remove the stem_image anyways
        try:
            f = FileModel().load(stem_image['fileId'], level=AccessType.READ,
                                 user=user)
            if f.get('imported', False) is True:
                if f['itemId'] == self._get_import_stem_item(user)['_id']:
                    FileModel().remove(f)
        except:
            pass

        return self.remove(stem_image)

    def _get_file(self, stem_image, user):
        """Get a file object of the stem image"""
        girder_file = FileModel().load(stem_image['fileId'],
                                       level=AccessType.READ, user=user)
        return FileModel().open(girder_file)

    def _get_h5_dataset(self, id, user, path):
        stem_image = self.load(id, user=user, level=AccessType.READ)

        if not stem_image:
            raise RestException('StemImage not found.', code=404)

        f = self._get_file(stem_image, user)

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

    def bright(self, id, user):
        return self._get_h5_dataset(id, user, '/stem/bright')

    def dark(self, id, user):
        return self._get_h5_dataset(id, user, '/stem/dark')

    def _get_h5_dataset_shape(self, id, user, path):
        stem_image = self.load(id, user=user, level=AccessType.READ)

        if not stem_image:
            raise RestException('StemImage not found.', code=404)

        f = self._get_file(stem_image, user)
        with h5py.File(f, 'r') as f:
            return f[path].shape

    def bright_shape(self, id, user):
        return self._get_h5_dataset_shape(id, user, '/stem/bright')

    def dark_shape(self, id, user):
        return self._get_h5_dataset_shape(id, user, '/stem/dark')

    def _get_import_stem_item(self, user):
        """Get the item where we will store stem images

        A new folder and item will be created if they do not exist.
        Otherwise, they will be reused.

        """
        folder = FolderModel().createFolder(user, StemImage.IMPORT_FOLDER,
                                            parentType='user', public=False,
                                            creator=user, reuseExisting=True)

        return ItemModel().createItem(StemImage.IMPORT_ITEM_NAME, user, folder,
                                      reuseExisting=True)

    def _get_import_unique_file_name(self, item):
        """Get a unique name of a file to go in the item"""
        files = ItemModel().childFiles(item)
        names = [x['name'] for x in files]
        for i in range(1, 1000):
            if str(i) not in names:
                return str(i)

        raise RestException('Too many files in item:\n' + str(item), code=400)

    def _get_assetstore(self):
        """Gets the asset store and ensures it is a file system"""
        assetstore = AssetstoreModel().getCurrent()
        if assetstore['type'] is not AssetstoreType.FILESYSTEM:
            raise RestException('Current assetstore is not a file system!',
                                code=400)
        return assetstore
