import os

import h5py
import numpy as np

from girder.api.rest import setResponseHeader, RestException
from girder.constants import AccessType
from girder.models.file import File as FileModel
from girder.models.model_base import AccessControlledModel

class StemImage(AccessControlledModel):

    def __init__(self):
        super(StemImage, self).__init__()

    def initialize(self):
        self.name = 'StemImage'

        self.exposeFields(level=AccessType.READ, fields=(
           '_id', 'filePath', 'fileId'))

    def filter(self, stem_image, user):
        stem_image = super(StemImage, self).filter(doc=stem_image, user=user)

        del stem_image['_accessLevel']
        del stem_image['_modelType']

        return stem_image

    def validate(self, doc):
        # Ensure the fileId or filePath are valid
        if 'fileId' in doc:
            file = FileModel().load(doc['fileId'], level=AccessType.READ)
            doc['fileId'] = file['_id']
        elif 'filePath' in doc:
            if not os.path.isfile(doc['filePath']):
                msg = 'File does not exist: ' + doc['filePath']
                raise RestException(msg, code=400)
        else:
            raise RestException('Neither fileId nor filePath are set',
                                code=400)

        return doc

    def create(self, user, fileId=None, filePath=None, public=False):
        stem_image = {}
        if fileId:
            stem_image['fileId'] = fileId
        elif filePath:
            stem_image['filePath'] = filePath
        else:
            raise RestException('Must set either fileId or filePath',
                                code=400)

        self.setUserAccess(stem_image, user=user, level=AccessType.ADMIN)
        if public:
            self.setPublic(stem_image, True)

        return self.save(stem_image)

    def _get_h5_dataset(self, id, user, path):
        stem_image = self.load(id, user=user, level=AccessType.READ)

        if not stem_image:
            raise RestException('StemImage not found.', code=404)

        if 'fileId' in stem_image:
            girder_file = FileModel().load(stem_image['fileId'],
                                           level=AccessType.READ)
            f = FileModel().open(girder_file)
        elif 'filePath' in stem_image:
            f = stem_image['filePath']
        else:
            raise RestException('StemImage does not contain `fileId` nor '
                                '`filePath`.', code=400)

        def _stream():
            nonlocal f
            read_size = 10
            with h5py.File(f, 'r') as f:
                dataset = f[path]
                total_read = 0
                while total_read != dataset.shape[0]:
                    if total_read + read_size > dataset.shape[0]:
                        read_size = dataset.shape[0] - total_read

                    shape = (read_size,) + dataset.shape[1:]
                    array = np.empty(shape, dtype=dataset.dtype)

                    start = total_read
                    end = start + read_size

                    dataset.read_direct(array,
                                        source_sel=np.s_[start:end])
                    total_read += read_size
                    yield array.tobytes()

        return _stream

    def bright(self, id, user):
        setResponseHeader('Content-Type', 'application/octet-stream')
        return self._get_h5_dataset(id, user, '/stem/bright')

    def dark(self, id, user):
        setResponseHeader('Content-Type', 'application/octet-stream')
        return self._get_h5_dataset(id, user, '/stem/dark')
