import aiohttp
import logging
import sys

from stevedore import extension
import coloredlogs

_pipelines = {}

logger = logging.getLogger('stemworker')

async def authenticate(url, girder_api_key):
    params = {
        'girderApiKey': girder_api_key
    }
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        async with session.post('%s/login' % url, json=params) as resp:
            await resp.read()

    return resp.cookies['session'].output(header='')

def load_pipelines():

    global _pipelines
    mgr = extension.ExtensionManager(
        namespace='stempy.pipeline',
        invoke_on_load=False,
    )

    for p in mgr:
        if p.name in _pipelines:
            logger.warn('Pipeline already registered with name: %s' % p.name)

        cls = p.entry_point.resolve()

        display_name = None
        if hasattr(cls, 'NAME'):
            display_name = cls.NAME

        _pipelines[p.name] = cls

        msg = 'Registered pipeline: %s' % p.name
        if display_name is not None:
            msg = '%s - %s' % (msg, display_name)
        logger.info('Registered pipeline: %s.' % msg)

async def run(url, girder_api_key):

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = coloredlogs.ColoredFormatter('%(asctime)s,%(msecs)03d - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    logger.info('Loading pipelines.')
    load_pipelines()

    cookie = await authenticate(url, girder_api_key)
