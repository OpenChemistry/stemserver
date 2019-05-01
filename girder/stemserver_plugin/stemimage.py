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
        self.route('GET', (':id', 'bright'), self.bright)
        self.route('GET', (':id', 'dark'), self.dark)
        self.route('GET', (':id', 'bright', 'shape'), self.bright_shape)
        self.route('GET', (':id', 'dark', 'shape'), self.dark_shape)
        self.route('GET', (':id', 'frames', ':scan_position'), self.frame)
        self.route('GET', (':id', 'frames'), self.all_frames)
        self.route('GET', (':id', 'frames', 'detector_positions'),
                   self.detector_positions)
        self.route('GET', (':id', 'scan_positions'), self.scan_positions)
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

    @access.user
    @autoDescribeRoute(
        Description('Get the shape of the bright field of a stem image.')
        .param('id', 'The id of the stem image.')
    )
    def bright_shape(self, id):
        return self._model.bright_shape(id, getCurrentUser())

    @access.user
    @autoDescribeRoute(
        Description('Get the shape of the dark field of a stem image.')
        .param('id', 'The id of the stem image.')
    )
    def dark_shape(self, id):
        return self._model.dark_shape(id, getCurrentUser())

    @access.user
    @autoDescribeRoute(
        Description('Get a frame of an image (in bytes).')
        .param('id', 'The id of the stem image.')
        .param('scan_position', 'The scan position of the frame.',
               dataType='integer')
        .errorResponse('Scan position is out of bounds')
    )
    def frame(self, id, scan_position):
        return self._model.frame(id, getCurrentUser(), scan_position)

    @access.user
    @autoDescribeRoute(
        Description('Get all frames of an image (in msgpack format).')
        .param('id', 'The id of the stem image.')
    )
    def all_frames(self, id):
        return self._model.all_frames(id, getCurrentUser())

    @access.user
    @autoDescribeRoute(
        Description('Get the detector positions of an image.')
        .param('id', 'The id of the stem image.')
    )
    def detector_positions(self, id):
        return self._model.detector_positions(id, getCurrentUser())

    @access.user
    @autoDescribeRoute(
        Description('Get the scan positions of an image (in bytes).')
        .param('id', 'The id of the stem image.')
    )
    def scan_positions(self, id):
        return self._model.scan_positions(id, getCurrentUser())

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
