from setuptools import setup, find_packages

setup(
    name = 'stemworker',
    version = '0.0.1',
    url = 'https://github.com/OpenChemistry/stemserver.git',
    description = 'STEM pipeline worker.',
    packages = find_packages(),
    install_requires = [
        'click'
    ],
    entry_points= {
        'console_scripts': [
            'stemworker=stemworker.cli:main'
        ]
    }
)