from girder.api.rest import RestException
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
            pass
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
