from setuptools import setup, find_packages

setup(
    name = 'stemworker',
    version = '0.0.1',
    url = 'https://github.com/OpenChemistry/stemserver.git',
    description = 'STEM pipeline worker.',
    packages = find_packages(),
    install_requires = [
        'click',
        'aiohttp',
        'python-socketio[asyncio_client]',
        'mpi4py',
        'stevedore',
        'coloredlogs',
        'msgpack'
    ],
    entry_points= {
        'console_scripts': [
            'stemworker=stemworker.cli:main'
        ],
        'stempy.pipeline': [
            'annular = stemworker.pipelines.annular_mask:execute',
            'maximum_diffraction = stemworker.pipelines.maximum_diffraction:execute'
        ]
    }
)
