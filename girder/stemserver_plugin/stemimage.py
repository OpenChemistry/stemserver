from girder.api.describe import Description, autoDescribeRoute
from girder.api import access
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

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Create a stem image')
        .param('fileId', 'The file id of the image.', required=False)
        .param('filePath', 'The file path to the image.', required=False)
    )
    def create(self, params):
        user = getCurrentUser()
        fileId = params.get('fileId')
        filePath = params.get('filePath')

        return self._clean(self._model.create(user, fileId, filePath))

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
