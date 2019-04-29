from girder import plugin
from .stemimage import StemImage


class StemPlugin(plugin.GirderPlugin):
    DISPLAY_NAME = 'STEM'

    def load(self, info):
        info['apiRoot'].stem_images = StemImage()
