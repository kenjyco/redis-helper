import os.path
import urllib.request
import click
from os import makedirs, chdir


SCRIPT_URL_BASE = 'https://raw.githubusercontent.com/kenjyco/redis-helper/master/redis_helper/scripts/'
SCRIPT_FILES = [
    'download_examples.py',
    'download_scripts.py',
    'notes.py',
    'shell.py',
]


@click.command()
@click.argument('directory', default='.', type=click.Path())
def main(directory):
    """Download redis-helper script files from github"""
    directory = os.path.abspath(os.path.expanduser(directory))
    if not os.path.isdir(directory):
        makedirs(directory)
    chdir(directory)
    for filename in SCRIPT_FILES:
        print('saving {}'.format(repr(filename)))
        urllib.request.urlretrieve(SCRIPT_URL_BASE + filename, filename)


if __name__ == '__main__':
    main()
