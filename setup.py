from setuptools import setup, find_packages


with open('README.rst', 'r') as fp:
    long_description = fp.read()

with open('requirements.txt', 'r') as fp:
    requirements = fp.read().splitlines()

setup(
    name='redis-helper',
    version='0.4.8',
    description='Easily store, index, and modify Python dicts in Redis (with flexible searching)',
    long_description=long_description,
    author='Ken',
    author_email='kenjyco@gmail.com',
    license='MIT',
    url='https://github.com/kenjyco/redis-helper',
    download_url='https://github.com/kenjyco/redis-helper/tarball/v0.4.8',
    packages=find_packages(),
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    install_requires=requirements,
    include_package_data=True,
    package_dir={'': '.'},
    package_data={
        '': ['*.ini'],
    },
    entry_points={
        'console_scripts': [
            'rh-download-examples=redis_helper.scripts.download_examples:main',
            'rh-download-scripts=redis_helper.scripts.download_scripts:main',
            'rh-notes=redis_helper.scripts.notes:main',
            'rh-shell=redis_helper.scripts.shell:main',
            'rh-collection-reports=redis_helper.scripts.collection_reports:main',
            'rh-clear-all-locks=redis_helper.scripts.clear_locks:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries',
        'Topic :: Utilities',
    ],
    keywords=['redis', 'cli', 'command-line', 'dictionary', 'data', 'database', 'secondary index', 'model', 'prototype', 'event logging', 'dashboard', 'easy modeling', 'helper', 'kenjyco']
)
