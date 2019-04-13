# Demo: https://asciinema.org/a/75kl95ty9vg2jl93pfz9fbs9q?t=1:00

import redis_helper as rh
from pprint import pprint


urls = rh.Collection(
    'web',
    'url',
    unique_field='name',
    index_fields='domain, _type'
)


def add_urls():
    urls.add(
        name='mini-16.04.bash',
        url='https://raw.githubusercontent.com/kenjyco/x200/master/sysinstall/apt-get/mini-16.04.bash',
        domain='githubusercontent.com',
        subdomain='raw',
        _type='setup_script',
    )
    urls.add(
        name='x200 sysinstall readme',
        url='https://github.com/kenjyco/x200/blob/master/sysinstall/apt-get/README.md',
        domain='github.com',
        _type='markdown',
    )
    urls.add(
        name='dotfiles Background.md',
        url='https://github.com/kenjyco/dotfiles/blob/master/Background.md',
        domain='github.com',
        _type='markdown',
    )
    urls.add(
        name='x200 Beginners-Guide.md',
        url='https://github.com/kenjyco/x200/blob/master/Beginners-Guide.md',
        domain='github.com',
        _type='markdown',
    )
    urls.add(
        name='learning-python3.ipynb',
        url='https://gist.githubusercontent.com/kenjyco/69eeb503125035f21a9d/raw/learning-python3.ipynb',
        domain='githubusercontent.com',
        subdomain='gist',
        _type='notebook',
    )
    urls.add(
        name='github kenjyco',
        url='https://github.com/kenjyco',
        domain='github.com',
        _type='profile',
    )
    urls.add(
        name='asciinema kenjyco',
        url='https://asciinema.org/~kenjyco',
        domain='asciinema.org',
        _type='profile',
    )
    urls.add(
        name='imgur kenjyco',
        url='https://kenjyco.imgur.com/',
        domain='imgur.com',
        subdomain='kenjyco',
        _type='profile',
    )
    urls.add(
        name='x200 github',
        url='https://github.com/kenjyco/x200',
        domain='github.com',
        _type='repo',
    )
    urls.add(
        name='dotfiles github',
        url='https://github.com/kenjyco/dotfiles',
        domain='github.com',
        _type='repo',
    )
    urls.add(
        name='input-helper github',
        url='https://github.com/kenjyco/input-helper',
        domain='github.com',
        _type='repo',
    )
    urls.add(
        name='redis-helper github',
        url='https://github.com/kenjyco/redis-helper',
        domain='github.com',
        _type='repo',
    )
    urls.add(
        name='mocp github',
        url='https://github.com/kenjyco/mocp',
        domain='github.com',
        _type='repo',
    )
    urls.add(
        name='rh-basics-1',
        url='https://asciinema.org/a/101422?t=1:10',
        domain='asciinema.org',
        _type='demo',
    )
    urls.add(
        name='rh-basics-1 change timezone',
        url='https://asciinema.org/a/101422?t=10:33',
        domain='asciinema.org',
        _type='demo',
    )
    urls.add(
        name='request_logs.py',
        url='https://raw.githubusercontent.com/kenjyco/redis-helper/master/examples/request_logs.py',
        domain='githubusercontent.com',
        subdomain='raw',
        _type='example',
    )
    urls.add(
        name='urls.py',
        url='https://raw.githubusercontent.com/kenjyco/redis-helper/master/examples/urls.py',
        domain='githubusercontent.com',
        subdomain='raw',
        _type='example',
    )
    urls.add(
        name='redis-helper pypi',
        url='https://pypi.python.org/pypi/redis-helper',
        domain='python.org',
        subdomain='pypi',
        _type='package',
    )
    urls.add(
        name='input-helper pypi',
        url='https://pypi.python.org/pypi/input-helper',
        domain='python.org',
        subdomain='pypi',
        _type='package',
    )
    urls.add(
        name='mocp pypi',
        url='https://pypi.python.org/pypi/mocp',
        domain='python.org',
        subdomain='pypi',
        _type='package',
    )
    urls.add(
        name='dotfiles commit 1',
        url='https://github.com/kenjyco/dotfiles/commit/8ab93fcbef3fbc8e1bf64e5eb7826f533c29ad8c',
        domain='github.com',
        _type='commit',
    )
    urls.add(
        name='dotfiles commit 2',
        url='https://github.com/kenjyco/dotfiles/commit/653e91ea40da6d2f31471eeedb58fb5ca963ce80',
        domain='github.com',
        _type='commit',
    )
    urls.add(
        name='sleepy_random_threads gist',
        url='https://gist.github.com/kenjyco/01ac345bf6c6e44577b1',
        domain='github.com',
        subdomain='gist',
        _type='example',
    )
    urls.add(
        name='wallpapers landscape.md',
        url='https://github.com/kenjyco/dotfiles/blob/master/wallpapers/landscape.md',
        domain='github.com',
        _type='markdown',
    )
    urls.add(
        name='yodawg-notes.md',
        url='https://github.com/kenjyco/x200/blob/master/yodawg-notes.md',
        domain='github.com',
        _type='markdown',
    )


if __name__ == '__main__':
    if urls.size == 0:
        print('\nRun `add_urls()` to add some sample urls')
    else:
        print('\nurls size:', urls.size)
        print('\nTop 3 index values per index:')
        pprint(urls.index_field_info(3))

        item_format = '"{name}" is a {_type} on {domain}... url={url}'
        print('\nHere is a random selection from the collection')
        print('using item_format={}\n'.format(repr(item_format)))
        print(urls.random(item_format=item_format))
