from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.docs import addModel
from girder.api.rest import Resource
from girder.api.rest import RestException
from girder.api.rest import getCurrentUser

from girder.constants import AccessType
from girder.constants import TokenScope

from .models.stemimage import StemImage as StemImageModel


class StemImage(Resource):

    def __init__(self):
        super(StemImage, self).__init__()
        self.resourceName = 'stem_image'
        self.route('GET', (), self.find)
        self.route('GET', (':id', 'bright'), self.bright)
        self.route('GET', (':id', 'dark'), self.dark)
        self.route('POST', (), self.create)
        self.route('DELETE', (':id',), self.delete)

        self._model = StemImageModel()

    def _clean(self, doc):
        if 'access' in doc:
            del doc['access']

        return doc

    @access.public
    @autoDescribeRoute(
        Description('Get stem images')
    )
    def find(self, params):
        stem_images = self._model.find()

        # Filter based upon access level.
        user = getCurrentUser()
        return [self._clean(self._model.filter(x, user)) for x in stem_images]

    @access.user
    @autoDescribeRoute(
        Description('Get the bright field of a stem image.')
        .param('id', 'The id of the stem image.')
    )
    def bright(self, id):
        return self._model.bright(id, getCurrentUser())

    @access.user
    @autoDescribeRoute(
        Description('Get the dark field of a stem image.')
        .param('id', 'The id of the stem image.')
    )
    def dark(self, id):
        return self._model.dark(id, getCurrentUser())

    addModel('StemImage', 'StemImageParams', {
        'id': 'StemImageParams',
        'properties': {
            'fileId': {
                'type': 'string',
                'description': 'The girder file ID of the image.'
            },
            'filePath': {
                'type': 'string',
                'description': 'The file path to the image on the girder server.'
            }
        }
    })
    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Create a stem image.')
        .jsonParam('body',
               'Should contain either `fileId` (a valid girder fileId of '
               'the image file) or `filePath` (a valid file path on the '
               'girder server to the image file).',
               paramType='body', dataType='StemImage')
        .errorResponse('Failed to create stem image', code=400)
    )
    def create(self, body, params):
        user = self.getCurrentUser()

        fileId = body.get('fileId')
        filePath = body.get('filePath')
        public = body.get('public', False)

        return self._clean(self._model.create(user, fileId, filePath, public))

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Delete a stem image.')
        .param('id', 'The id of the stem image to be deleted.')
        .errorResponse('StemImage not found.', 404)
    )
    def delete(self, id):
        user = self.getCurrentUser()
        stem_image = StemImageModel().load(id, user=user,
                                           level=AccessType.WRITE)

        if not stem_image:
            raise RestException('StemImage not found.', code=404)

        return StemImageModel().remove(stem_image)
