import socketio
import asyncio
import random
import sys
import numpy as np
import click
import aiohttp

async def node_job(i, n, values, client):
    await asyncio.sleep(2 * random.random())
    size = len(values) // n
    start = i * size
    stop = start + size
    if (i == n - 1):
        stop = len(values)

    noise = 1.0 + (0.5 - np.random.rand(stop - start)) * 0.0005

    pixel_indices = np.array(range(start, stop), dtype=np.uint32)
    pixels = np.array(values[pixel_indices], dtype=np.float64) * noise

    message = {
        'data': {
            'values': pixels.tobytes(),
            'indexes': pixel_indices.tobytes()
        }
    }
    await client.emit('stem.dark', message, namespace='/stem')

    message['data']['values'] = (pixels * -1.0).tobytes()
    await client.emit('stem.bright', message, namespace='/stem')

async def authenticate(url, girder_api_key):
    params = {
        'girderApiKey': girder_api_key
    }
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        async with session.post('%s/login' % url, json=params) as resp:
            await resp.read()

    return resp.cookies['session'].output(header='')

async def main(url, n, girder_api_key):
    dark_field = np.load('./dark.npy')
    width, height = dark_field.shape
    values = dark_field.flatten()

    cookie = await authenticate(url, girder_api_key)

    client = socketio.AsyncClient()

    @client.on('connect', namespace='/stem')
    async def on_connect():
        print('Connected')
        await client.emit('stem.worker_connected', namespace='/stem')

    @client.on('stem.generate', namespace='/stem')
    async def on_generate(parameters):
        await client.emit('stem.size',  {'width': str(width), 'height': str(height)}, namespace='/stem')

        tasks = []
        for i in range(n):
            tasks.append(asyncio.create_task(node_job(i, n, values, client)))

        await asyncio.gather(*tasks)

    @client.on('disconnect', namespace='/stem')
    async def on_disconnect():
        print('disconnected')

    headers = {
        'Cookie': cookie
    }
    await client.connect(url, namespaces=['/stem'], transports=['websocket'], headers=headers)

    # await client.disconnect()

@click.command()
@click.option('-u', '--flask-url', default='http://localhost:5000', help='URL for the flask server')
@click.option('-k', '--girder-api-key', envvar='GIRDER_API_KEY', default=None,
              help='[default: GIRDER_API_KEY env. variable]', required=True)
@click.option('-n', '--num-tasks', type=int, default=1, help='number of tasks')
def cli(flask_url, girder_api_key, num_tasks):
    loop = asyncio.get_event_loop()
    try:
        asyncio.ensure_future(main(flask_url, num_tasks, girder_api_key))
        loop.run_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    cli()
