import os.path
import urllib.request
import click
from os import makedirs, chdir


EXAMPLE_URL_BASE = 'https://raw.githubusercontent.com/kenjyco/redis-helper/master/examples/'
EXAMPLE_FILES = [
    'request_logs.py',
    'urls.py',
]


@click.command()
@click.option(
    '--directory', '-d', 'directory', default='.', type=click.Path(),
    help='directory to downloaded examples to'
)
def main(directory):
    """Download redis-helper example files from github"""
    directory = os.path.abspath(os.path.expanduser(directory))
    if not os.path.isdir(directory):
        makedirs(directory)
    chdir(directory)
    for filename in EXAMPLE_FILES:
        print('saving {}'.format(repr(filename)))
        urllib.request.urlretrieve(EXAMPLE_URL_BASE + filename, filename)


if __name__ == '__main__':
    main()
