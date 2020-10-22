from setuptools import setup, find_packages


with open('README.rst', 'r') as fp:
    long_description = fp.read()

setup(
    name='redis-helper',
    version='0.3.44',
    description='Easily store, index, and modify Python dicts in Redis (with flexible searching)',
    long_description=long_description,
    author='Ken',
    author_email='kenjyco@gmail.com',
    license='MIT',
    url='https://github.com/kenjyco/redis-helper',
    download_url='https://github.com/kenjyco/redis-helper/tarball/v0.3.44',
    packages=find_packages(),
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    install_requires=[
        'bg-helper',
        'click>=6.0',
        'dt-helper',
        'fs-helper',
        'hiredis==0.2.0',
        'input-helper',
        'pytz',
        'redis==2.10.5',
        'settings-helper',
        'ujson==1.35',
    ],
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
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries',
        'Intended Audience :: Developers',
    ],
    keywords=['redis', 'dictionary', 'secondary index', 'model', 'log', 'prototype', 'helper']
)
