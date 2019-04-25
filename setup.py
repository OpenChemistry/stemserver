from setuptools import setup, find_packages

setup(
    name = 'stemserver',
    version = '0.0.1',
    url = 'https://github.com/OpenChemistry/stemserver.git',
    description = 'Flask SockIO app to server STEM data.',
    packages = find_packages(),
    install_requires = [
        'flask-socketio',
        'eventlet'
    ]
)
