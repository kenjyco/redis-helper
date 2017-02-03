from setuptools import setup, find_packages


with open('README.rst', 'r') as fp:
    long_description = fp.read()

setup(
    name='redis-helper',
    version='0.3.4',
    description='Easily store, index, and modify Python dicts in Redis (with flexible searching)',
    long_description=long_description,
    author='Ken',
    author_email='kenjyco@gmail.com',
    license='MIT',
    url='https://github.com/kenjyco/redis-helper',
    download_url='https://github.com/kenjyco/redis-helper/tarball/v0.3.4',
    packages=find_packages(),
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    install_requires=[
        'redis==2.10.5',
        'hiredis==0.2.0',
        'ujson==1.35',
        'pytz',
        'input-helper',
    ],
    include_package_data=True,
    package_dir={'': '.'},
    package_data={
        '': ['*.ini'],
    },
    entry_points={
        'console_scripts': [
            'rh-download-examples=redis_helper:download_examples',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries',
        'Intended Audience :: Developers',
    ],
    keywords=['redis', 'dictionary', 'secondary index', 'events', 'model', 'log', 'data', 'helper']
)
