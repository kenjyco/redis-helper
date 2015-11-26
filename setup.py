from setuptools import setup

setup(
    name='redis_helper',
    version='0.1.0',
    description='Helper functions to store/retreive redis objects',
    author='Ken',
    author_email='kenjyco@gmail.com',
    packages=['redis_helper'],
    install_requires=[
        'redis>=2.10,<3.0',
    ],
)
