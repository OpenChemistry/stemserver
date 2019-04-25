import socketio
import asyncio
import random
import sys
import numpy as np

async def job(i, n, values, client):
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
    client.emit('stem.bright', message, namespace='/stem')

async def main(url, n):
    dark_field = np.load('./dark.npy')
    width, height = dark_field.shape
    values = dark_field.flatten()

    client = socketio.Client()

    @client.on('connect')
    def on_connect():
        print('Connected')

    client.connect(url, namespaces=['/stem'])

    iteration = 0
    while True:
        client.emit('stem.size',  {'width': str(width), 'height': str(height)}, namespace='/stem')
        tasks = []

        for i in range(n):
            tasks.append(asyncio.create_task(job(i, n, values, client)))

        for task in tasks:
            await task

        iteration += 1

    client.disconnect()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise Exception('Pass url and number of tasks')
    url = sys.argv[1]
    n = int(sys.argv[2])
    asyncio.run(main(url, n))

