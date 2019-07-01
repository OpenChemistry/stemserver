import asyncio

loop = asyncio.get_event_loop()

try:
    loop.run_forever()
except KeyboardInterrupt:
    print('KILL')
    loop.stop()
finally:
    print('DONE')
    loop.close()

