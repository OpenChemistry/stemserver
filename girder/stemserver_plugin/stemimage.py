from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.api.rest import getCurrentUser

from girder.constants import TokenScope

from .models.stemimage import StemImage as StemImageModel


class StemImage(Resource):

    def __init__(self):
        super(StemImage, self).__init__()
        self.resourceName = 'stem_images'
        self.route('GET', (), self.find)
        self.route('GET', (':id', 'names'), self.image_names)
        self.route('GET', (':id', ':name'), self.image)
        self.route('GET', (':id', ':name', 'shape'), self.image_shape)
        self.route('GET', (':id', 'frames', ':scanPosition'), self.frame)
        self.route('GET', (':id', 'frames'), self.all_frames)
        self.route('GET', (':id', 'frames', 'shape'), self.frame_shape)
        self.route('GET', (':id', 'scanPositions'), self.scan_positions)
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
        user = getCurrentUser()
        results = self._model.findWithPermissions(user=user)
        return [self._clean(x) for x in results]

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get the names of the available stem images.')
        .param('id', 'The id of the stem image.')
    )
    def image_names(self, id):
        return self._model.image_names(id, getCurrentUser())

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get a stem image.')
        .param('id', 'The id of the stem image.')
        .param('name', 'The name or index of the stem image.')
        .param('format',
               'The format with which to send the data over http. '
               'Currently either bytes (default) or msgpack.',
               required=False)
    )
    def image(self, id, format, name):
        return self._model.image(id, getCurrentUser(), format, name)

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get the shape of a stem image.')
        .param('id', 'The id of the stem image.')
        .param('name', 'The name or index of the stem image.')
    )
    def image_shape(self, id, name):
        return self._model.image_shape(id, getCurrentUser(), name)

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get a frame of an image.')
        .param('id', 'The id of the stem image.')
        .param('scanPosition', 'The scan position of the frame.')
        .param('type',
               'The type of data to use. Options: electron (default) or raw',
               default='electron')
        .param('format',
               'The format with which to send the data over http. '
               'Currently either bytes (default) or msgpack',
               required=False)
        .errorResponse('Scan position is out of bounds')
    )
    def frame(self, id, scanPosition, type, format):
        return self._model.frame(id, getCurrentUser(), int(scanPosition), type, format)

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get all frames of an image (msgpack format only).')
        .param('id', 'The id of the stem image.')
        .param('type',
               'The type of data to use. Options: electron (default) or raw',
               default='electron')
        .param('limit',
               'Limit the number of diffractograms to prevent timeout',
               required=False)
        .param('offset',
               'Offset to use with the limit',
               required=False)
    )
    def all_frames(self, id, type, limit, offset):
        return self._model.all_frames(id, getCurrentUser(), type, limit,
                                      offset)

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get the detector dimensions of an image.')
        .param('id', 'The id of the stem image.')
        .param('type',
               'The type of data to use. Options: electron (default) or raw',
               default='electron')
    )
    def frame_shape(self, id, type):
        return self._model.frame_shape(id, getCurrentUser(), type)

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get the scan positions of an image.')
        .param('id', 'The id of the stem image.')
        .param('type',
               'The type of data to use. Options: electron (default) or raw',
               default='electron')
    )
    def scan_positions(self, id, type):
        return self._model.scan_positions(id, getCurrentUser(), type)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Create a stem image.')
        .jsonParam('body',
                   'Should contain either `fileId` (a valid girder fileId of '
                   'the image file) or `filePath` (a valid file path on the '
                   'girder server to the image file (admin users only)).',
                   paramType='body')
        .errorResponse('Failed to create stem image')
    )
    def create(self, body, params):
        user = self.getCurrentUser()

        file_id = body.get('fileId')
        file_path = body.get('filePath')
        public = body.get('public', False)

        return self._clean(self._model.create(user, file_id, file_path,
                                              public))

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Delete a stem image.')
        .param('id', 'The id of the stem image to be deleted.')
        .errorResponse('StemImage not found.', 404)
    )
    def delete(self, id):
        return self._model.delete(id, self.getCurrentUser())
