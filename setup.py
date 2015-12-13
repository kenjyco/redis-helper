from setuptools import setup

setup(
    name='redis-helper',
    version='0.1.0',
    description='Helper functions to store/retrieve redis objects',
    author='Ken',
    author_email='kenjyco@gmail.com',
    license='MIT',
    url='https://github.com/kenjyco/redis_helper',
    download_url='https://github.com/kenjyco/redis_helper/tarball/v0.1.0',
    packages=['redis_helper'],
    install_requires=[
        'redis>=2.10,<3.0',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries',
        'Intended Audience :: Developers',
    ],
    keywords = ['redis']
)
