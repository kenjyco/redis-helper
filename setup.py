import os.path
from setuptools import setup


home_config_dir = os.path.expanduser('~/.config/redis-helper')
setup(
    name='redis-helper',
    version='0.2.4',
    description='Easily store, index, and modify Python dicts in Redis (with flexible searching)',
    author='Ken',
    author_email='kenjyco@gmail.com',
    license='MIT',
    url='https://github.com/kenjyco/redis_helper',
    download_url='https://github.com/kenjyco/redis_helper/tarball/v0.2.4',
    packages=['redis_helper'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    install_requires=[
        'redis==2.10.5',
        'hiredis==0.2.0',
        'ujson==1.35',
        'pytz',
    ],
    include_package_data=True,
    data_files=[(home_config_dir, ['settings.ini', 'examples/request_logs.py'])],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries',
        'Intended Audience :: Developers',
    ],
    keywords = ['redis', 'dictionary', 'secondary index', 'events', 'model', 'log', 'data']
)
