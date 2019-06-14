import aiohttp

async def authenticate(url, girder_api_key):
    params = {
        'girderApiKey': girder_api_key
    }
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        async with session.post('%s/login' % url, json=params) as resp:
            await resp.read()

    return resp.cookies['session'].output(header='')

async def run(url, girder_api_key):
    cookie = await authenticate(url, girder_api_key)
