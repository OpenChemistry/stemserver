import asyncio
import logging
import sys
import uuid
import inspect
import functools
from collections import OrderedDict

import aiohttp
from stevedore import extension
import coloredlogs
import msgpack
from mpi4py import MPI

_pipelines = {}
_pipeline_instances = {}

logger = logging.getLogger('stemworker')

def get_pipeline_instance(id):
    return _pipeline_instances[id]

def delete_pipeline_instance(id):
    del _pipeline_instances[id]

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
        logger.info(msg)

def create_pipeline_instance(name):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()

    pipeline_id = None
    if rank == 0:
        pipeline_id = uuid.uuid4().hex

    pipeline_id = comm.bcast(pipeline_id, root=0)

    # Look up pipeline
    if name not in _pipelines:
        raise Exception('Unable to find pipeline: %s' % name)

    pipeline = _pipelines[name]

    if inspect.isclass(pipeline):
        instance = pipeline()
        pipeline = instance.execute

    _pipeline_instances[pipeline_id] = {
        'name': name,
        'executor': pipeline
    }

    return pipeline_id

def get_pipeline_info(name, pipelines):
    pipeline = pipelines.get(name)
    if pipeline is None:
        raise Exception('Unable to find pipeline: %s' % name)
    return {
        'name': name,
        'displayName': pipeline.NAME,
        'description': pipeline.DESCRIPTION,
        'parameters': OrderedDict([(k, pipeline.PARAMETERS[k]) for k in reversed(pipeline.PARAMETERS)]),
        'input': pipeline.INPUT,
        'output': pipeline.OUTPUT,
        'aggregation': pipeline.AGGREGATION
    }

async def run(url, girder_api_key):
    from stemworker import socketio

    global _pipelines
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = coloredlogs.ColoredFormatter('%(asctime)s,%(msecs)03d - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    logger.info('Loading pipelines.')
    load_pipelines()

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()

    worker_id = None
    if rank == 0:
        worker_id = uuid.uuid4().hex

    worker_id = comm.bcast(worker_id, root=0)

    cookie = await authenticate(url, girder_api_key)
    await socketio.connect(_pipelines, worker_id, url, cookie)
