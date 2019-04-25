import pytest

from girder.plugin import loadedPlugins


@pytest.mark.plugin('stem')
def test_import(server):
    assert 'stem' in loadedPlugins()
