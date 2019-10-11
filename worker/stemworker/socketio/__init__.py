import logging
import asyncio
import functools
import glob
from collections import OrderedDict

from mpi4py import MPI
import socketio
import msgpack
import h5py

from stemworker import (
    create_pipeline_instance,
    get_pipeline_instance,
    delete_pipeline_instance
)

from .constants import FileFormat

from stempy import io

logger = logging.getLogger('stemworker')

def get_worker_reader(path, version):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    world_size = comm.Get_size()
    files = glob.glob(path)[rank::world_size]
    if (len(files) == 0):
        return None
    return io.reader(files, version=int(version))

def get_worker_h5_reader(path):
    comm = MPI.COMM_WORLD
    if comm.Get_size() > 1:
        return h5py.File(path, 'r', driver='mpio', comm=comm)
    else:
        return h5py.File(path, 'r')

async def connect(pipelines,  worker_id, url, cookie):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    client = socketio.AsyncClient()

    @client.on('connect', namespace='/stem')
    async def on_connect():
        logger.info('Connected to stemserver.')

        connect_data = {
            'id': worker_id,
            'rank': rank
        }
        # If we are rank 0 then send the list of pipelines we support
        if rank == 0:
            pipeline_definitions = {}

            for (name, pipeline) in pipelines.items():
                p = {
                    'name': name,
                    'displayName': pipeline.NAME,
                    'description': pipeline.DESCRIPTION,
                    'parameters': OrderedDict([(k, pipeline.PARAMETERS[k]) for k in reversed(pipeline.PARAMETERS)])
                }
                pipeline_definitions[name] = p

            connect_data['pipelines'] =  pipeline_definitions

        await client.emit('stem.worker_connected', namespace='/stem',
                          data=connect_data)

    @client.on('stem.pipeline.create', namespace='/stem')
    async def on_create(params):
        logger.info('stem.pipeline.create: %s' % params)
        worker_id = params['workerId']
        name = params['name']
        pipeline_id = create_pipeline_instance(name)
        comm.barrier()

        if rank == 0:
            await client.emit('stem.pipeline.created', namespace='/stem', data={
                # Include the id so we know who to send the message to.
                'id': params['id'],
                'name': name,
                'workerId': worker_id,
                'pipelineId': pipeline_id
            })

    @client.on('stem.pipeline.execute', namespace='/stem')
    async def on_execute(params):
        logger.info('stem.pipeline.execute: %s' % params)
        pipeline_id = params['pipelineId']
        pipeline = get_pipeline_instance(pipeline_id)

        file_format = params['params'].get('format')
        path = params['params'].get('path')
        version = params['params'].get('version', 3)
        reader = None
        if file_format == FileFormat.Dat:
            reader = get_worker_reader(path, version)
        elif file_format == FileFormat.H5:
            reader = get_worker_h5_reader(path)

        if reader is not None:
            loop = asyncio.get_running_loop()
            # Add the kwargs
            pipeline = functools.partial(pipeline, reader, **params['params'])
            # Execute in thread pool
            result = await loop.run_in_executor(None, pipeline)

            if isinstance(reader, h5py.File):
                reader.close()

            data = {
                'workerId': worker_id,
                'rank': rank,
                'pipelineId': pipeline_id,
                'result': result.tolist()
            }
            data = msgpack.packb(data, use_bin_type=True)

            await client.emit('stem.pipeline.executed', namespace='/stem', data=data)

        comm.Barrier()
        if rank == 0:
            data = {
                'workerId': worker_id,
                'rank': rank,
                'pipelineId': pipeline_id,
            }
            await client.emit('stem.pipeline.completed', namespace='/stem', data=data)

    @client.on('stem.pipeline.delete', namespace='/stem')
    async def on_delete(params):
        logger.info('stem.pipeline.delete: %s' % params)
        pipeline_id = params['pipelineId']
        logger.info('Deleting pipeline:: %s' % pipeline_id)
        delete_pipeline_instance(pipeline_id)

    @client.on('disconnect', namespace='/stem')
    async def on_disconnect():
        logger.info('Client disconnected.')

    headers = {
        'Cookie': cookie
    }

    await client.connect(url, namespaces=['/stem'], transports=['websocket'], headers=headers)
