import click
import asyncio

from . import run

@click.command('stemworker')
@click.option('-u', '--flask-url', default='http://localhost:5000', help='URL for the flask server')
@click.option('-k', '--girder-api-key', envvar='GIRDER_API_KEY', default=None,
              help='[default: GIRDER_API_KEY env. variable]', required=True)
def main(flask_url, girder_api_key):
    loop = asyncio.get_event_loop()
    try:
        asyncio.ensure_future(run(flask_url, girder_api_key))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
