> Note: as of redis-helper v0.4.0, version 3.0 of redis-py is in use, which has
> backwards incompatible changes withe redis-py 2.x. See
> <https://github.com/andymccurdy/redis-py#upgrading-from-redis-py-2x-to-30>

## About

[redis-helper project]: https://github.com/kenjyco/redis-helper
[beu-fork]: https://github.com/kenjyco/beu/tree/4aea6146fc5f01df3e344b9fadddf28b795dac89
[Redis]: http://redis.io/topics/data-types-intro
[redis-helper package]: https://pypi.python.org/pypi/redis-helper
[request logging demo]: https://asciinema.org/a/101422?t=1:10
[urls demo]: https://asciinema.org/a/75kl95ty9vg2jl93pfz9fbs9q?t=1:00
[examples]: https://github.com/kenjyco/redis-helper/tree/master/examples
[settings.ini]: https://github.com/kenjyco/redis-helper/blob/master/redis_helper/settings.ini
[bg-helper docker tools]: https://github.com/kenjyco/bg-helper#helper-functions-in-bg_helpertools-that-use-docker-if-it-is-installed

Install redis-helper, create an instance of `redis_helper.Collection`
(**the args/kwargs define the model**) and use the `add`, `get`, `update`,
`delete`, and `find` methods to:

- quickly store/retrieve/modify Python dicts in Redis
- filter through indexed fields with simple/flexible find arguments
- power real-time dashboards with metrics at a variety of time ranges
- super-charge event logging and system debugging
- build FAST prototypes and simulators
- greatly simplify data access patterns throughout application

See the [request logging demo][] and [urls demo][] (with `unique_field`
defined). The [examples][] they reference are **short** and **easy to
read**.

The [redis-helper project][] evolved from a [reference Python project][beu-fork]
that would be **easy to teach** and follow many practical best practices and
useful patterns.  Main purpose was to have something that was super **easy to
configure** (a single `~/.config/redis-helper/settings.ini` file for multiple
application environments) that did cool things with [Redis][].

The [redis-helper package][] provides a `Collection` class that was designed to
be **easy to interact with** in the shell (for exploration, experimentation, and
debugging). Most methods on a `Collection` help **minimize typing** (passing
multiple arguments in a single delimited string when appropriate) and do "the
most reasonable thing" whenever possible.

The first time that `redis_helper` is imported, the sample
[settings.ini][] file will be copied to the `~/.config/redis-helper`
directory.

```
[default]
image_version = 6-alpine

[dev]
container_name = redis-helper
port = 6379
rm = False
redis_url = redis://localhost:6379/1

[test]
container_name = redis-helper-test
port = 6380
rm = True
redis_url = redis://localhost:6380/9
```

If docker is installed to your system and your user has permission to use it,
the [bg-helper docker tools][] will be used to start a redis container for
development or running tests, if Redis is not already installed locally.

## (Optionally) install Redis and start server locally

```
% sudo apt-get install -y redis-server

or

% brew install redis
% brew services start redis
```

## Install redis-helper

- install latest tag/release of [redis-helper package][]

    ```
    % pip3 install redis-helper
    ```
- or, install latest commit on master of [redis-helper project][]

    ```
    % pip3 install git+git://github.com/kenjyco/redis-helper
    ```

## Intro

[redis-py]: https://github.com/andymccurdy/redis-py
[StrictRedis]: https://redis-py.readthedocs.org/en/latest/#redis.StrictRedis
[ujson]: https://pypi.python.org/pypi/ujson
[dict]: https://docs.python.org/3/tutorial/datastructures.html#dictionaries
[hash]: https://redis.io/topics/data-types#hashes
[set]: https://redis.io/topics/data-types#sets
[sorted set]: https://redis.io/topics/data-types#sorted-sets
[hash commands]: http://redis.io/commands#hash
[set commands]: https://redis.io/commands#set
[sorted set commands]: https://redis.io/commands#sorted_set

[Redis][] is a fast in-memory **data structure server**, where each stored
object is referenced by a key name. Objects in Redis correspond to one of
several basic types, each having their own set of specialized commands to
perform operations. The [redis Python package][redis-py] provides the
[StrictRedis][] class, which contains methods that correspond to all of the
Redis server commands.

When initializing Collection objects, you must specify the "namespace" and
"name" of the collection (which are used to create the internally used
`_base_key` property). All Redis keys associated with a Collection will have a
name pattern that starts with the `_base_key`.

```python
import redis_helper as rh


request_logs = rh.Collection(
    'log',
    'request',
    index_fields='status, uri, host',
    json_fields='request, response, headers'
)

urls = rh.Collection(
    'web',
    'url',
    unique_field='name',
    index_fields='domain, _type'
)

notes = rh.Collection(
    'input',
    'note',
    index_fields='topic, tag',
    insert_ts=True
)

sample = rh.Collection(
    'ns',
    'sample',
    unique_field='name',
    index_fields='status',
    json_fields='data',
    rx_name='\S{4,6}',
    rx_status='(active|inactive|cancelled)',
    rx_aws='[a-z]+\-[0-9a-f]+',
    insert_ts=True
)

uses_sample = rh.Collection(
    'ns',
    'uses_sample',
    index_fields='z',
    rx_thing='\S{4,6}',
    reference_fields='thing--ns:sample'
)
```

- a `unique_field` can be specified on a collection if items in the collection
  should not contain duplicate values for that particular field
    - the `unique_field` cannot also be included in `json_fields` or
      `pickle_fields`
    - if you specify a `unique_field`, that field must exist on each item you
      add to the collection
- use `index_fields` to specify which fields you will want to filter on when
  using the `find` method
    - the values for data fields being indexed MUST be simple strings or numbers
    - the values for data fields being indexed SHOULD NOT be long strings, as
      the values themselves are part of the index keys
- use `json_fields` to specify which fields should be JSON encoded before
  insertion to Redis (using the very fast [ujson][] library)
- use `rx_{field}` to specify a regular expression for any field with strict
  rules for validation
- use `reference_fields` to specify fields that reference the `unique_field` of
  another collection
    - uses field--basekey combos
- use `pickle_fields` to specify which fields should be pickled before insertion
  to Redis
- set `insert_ts=True` to create an additional index to store insert times
    - only do this if you are storing items that you are likely to update and
      also likely to want to know the original insert time
        - each time an object is updated, the score associated with the
          `hash_id` (at the `_ts_zset_key`) is updated to the current timestamp
        - the score associated with the `hash_id` (at the `_in_zset_key`) is
          never updated

Essentially, you can store a Python [dict][] in a Redis [hash][] and index some
of the fields in Redis [sets][set]. The collection's `_ts_zset_key` is the Redis
key name for the [sorted set][] containing the `hash_id` of every hash in the
collection (with the `score` being a `utc_float` corresponding to the UTC time
the `hash_id` was added or modified).

- if `insert_ts=True` was passed in when initializing the `Collection` (or
  sub-class), then the collection will also define `self.in_zset_key` to be the
  Redis key name for the sorted set (for `hash_id` and `utc_float` of insert
  time)

```python
request_logs.add(
    method='get',
    status=400,
    host='blah.net',
    uri='/info',
    request={'x': 50, 'y': 100},
    response={'error': 'bad request'},
)

urls.add(
    name='redis-helper github',
    url='https://github.com/kenjyco/redis-helper',
    domain='github.com',
    _type='repo',
)
```

The `get` method is a wrapper to [hash commands][] `hget`, `hmget`, or
`hgetall`. The actual hash command that gets called is determined by the number of
fields requested.

- a Python dict is typically returned from `get`
- if `item_format` is specified, a string will be returned matching that format
  instead

```python
request_logs.get('log:request:1')
request_logs.get('log:request:1', 'host,status')
request_logs.get('log:request:1', item_format='{status} for {host}{uri}')
request_logs.get_by_position(0, item_format='{status} for {host}{uri}')
urls.get_by_position(-1, 'domain,url')
urls.get_by_unique_value('redis-helper github', item_format='{url} points to a {_type}')
```

- the `get_by_position` and `get_by_unique_value` methods are wrappers to `get`
    - the `get_by_unique_value` method is only useful if a `unique_field` was
      set on the Collection

The `find` method allows you to return data for items in the collection that
match some set of search criteria. Multiple search terms (i.e.
`index_field:value` pairs) maybe be passed in the `terms` parameter, as long as they are
separated by one of `,` `;` `|`. Any fields specified in the `get_fields`
parameter are passed along to the `get` method (when the actual fetching takes
place).

- when using `terms`, all terms that include the same field will be treatead
  like an "or" (union of related sets), then the intersection of different sets
  will be computed
- see the Redis [set commands][] and [sorted set commands][]

There are many options for specifying time ranges in the `find` method
including:

- `since` and `until` when specifying `num:unit` strings (i.e. 15:seconds,
  1.5:weeks, etc)
- `start_ts` and `end_ts` when specifying timestamps with a form between `YYYY`
  and `YYYY-MM-DD HH:MM:SS.f`
- `start` and `end` when specifying a `utc_float`
- for `since`, `until`, `start_ts`, and `end_ts`, multiple values may be passed
  in the string, as long as they are separated by one of `,` `;` `|`.
    - when multiple time ranges are specified, the `find` method will determine
      all reasonable combinations and return a result-set per combination
      (instead of returning a list of items, returns a dict of list of items)

If `count=True` is specified, the number of results matching the search criteria
are returned instead of the actual results

- if there are multiple time ranges specified, counts will be returned for each
  combination

```python
request_logs.find('status:400, host:blah.net', get_fields='uri,error')
request_logs.find(since='1:hr, 30:min', until='15:min, 5:min')
request_logs.find(count=True, since='1:hr, 30:min', until='15:min, 5:min')
urls.find(count=True, since='1:hr, 30:min, 10:min, 5:min, 1:min')
urls.find(start_ts='2017-02-03', end_ts='2017-02-03 7:15:00')
urls.find(start_ts='2017-02-03', item_format='{_ts} -> {_id}')
```

The `update` method allows you to change values for some fields (modifying the
`unique_field`, when it is specified, is not allowed).

- every time a field is modified for a particular `hash_id`, the previous value
  and score (timestamp) are stored in a Redis hash
- the `old_data_for_hash_id` or `old_data_for_unique_value` methods can be used
  to retrieve the history of all changes for a `hash_id`

```python
urls.update('web:url:1', _type='fancy', notes='this is a fancy url')
urls.old_data_for_hash_id('web:url:1')
urls.old_data_for_unique_value('redis-helper github')
```

The `load_ref_data` option on `get`, `get_by_unique_value`, or `find` methods
allow you to load the referenced data object from the other collection (where
`reference_fields` are specified)

```python
In [1]: sample.add(name='hello', aws='ami-0ad5743816d822b81', status='active')
Out[1]: 'ns:sample:1'

In [2]: uses_sample.add(thing='hello', z=500, y=True)
Out[2]: 'ns:uses_sample:1'

In [3]: uses_sample.get('ns:uses_sample:1')
Out[3]: {'thing': 'hello', 'z': 500, 'y': True}

In [4]: uses_sample.get('ns:uses_sample:1', load_ref_data=True)
Out[4]:
{'thing': {'name': 'hello',
  'aws': 'ami-0ad5743816d822b81',
  'status': 'active',
  '_id': 'ns:sample:1',
  '_ts': 20201028210044.875},
 'z': 500,
 'y': True}

In [5]: uses_sample.add(thing='byebye', z=100, y=True)
Out[5]: 'ns:uses_sample:2'

In [6]: uses_sample.get('ns:uses_sample:2', load_ref_data=True)
Out[6]: {'thing': 'byebye', 'z': 100, 'y': True}
```

## Tip

There may be times where you want to use redis-helper (if it's already
installed), but don't want to make it an explicit requirement of your project.
In cases like this you can do the following:

```
try:
    import redis_helper as rh
    from redis import ConnectionError as RedisConnectionError
except ImportError:
    SomeCollection = None
else:
    try:
        SomeCollection = rh.Collection(
            ...
        )
    except RedisConnectionError:
        SomeCollection = None
```

Then in whatever function, you can just do:

```
def some_func():
    if SomeCollection is None:
        return

    # Do stuff with SomeCollection
```

## Local development setup

[dev-setup.bash]: https://github.com/kenjyco/redis-helper/blob/master/dev-setup.bash

```
% git clone https://github.com/kenjyco/redis-helper
% cd redis-helper
% ./dev-setup.bash
```

The [dev-setup.bash][] script will create a virtual environment in the
`./venv` directory with extra dependencies (ipython, pdbpp, pytest), then copy
`settings.ini` to the `~/.config/redis-helper` directory.

## Running tests in development setup

[setup.cfg]: https://github.com/kenjyco/redis-helper/blob/master/setup.cfg
[pdb++]: https://pypi.python.org/pypi/pdbpp/
[debugging section]: https://github.com/kenjyco/redis-helper#settings-environments-testing-and-debugging
[project code]: https://github.com/kenjyco/redis-helper/tree/master/redis_helper
[test code]: https://github.com/kenjyco/redis-helper/tree/master/tests

The [setup.cfg][] file contains the options for `py.test`, currently
`-vsx -rs --pdb`.

The `-vsx -rs --pdb` options will run tests in a verbose manner and output the
reason why tests were skipped (if any were skipped). If there are any failing
tests, `py.test` will stop on the first failure and drop you into a [pdb++][]
debugger session.

See the [debugging section][] of the README for tips on using the debugger and
setting breakpoints (in the actual [project code][], or in the [test code][]).

```
% venv/bin/py.test
```

or

```
% venv/bin/python3 setup.py test
```

> Note: This option requires `setuptools` to be installed.

## Usage

The `rh-download-examples`, `rh-download-scripts`, `rh-notes`, and `rh-shell`
scripts are provided.

```
$ venv/bin/rh-download-examples --help
Usage: rh-download-examples [OPTIONS] [DIRECTORY]

  Download redis-helper example files from github

Options:
  --help  Show this message and exit.

$ venv/bin/rh-download-scripts --help
Usage: rh-download-scripts [OPTIONS] [DIRECTORY]

  Download redis-helper script files from github

Options:
  --help  Show this message and exit.

$ venv/bin/rh-notes --help
Usage: rh-notes [OPTIONS] [TOPIC]

  Prompt user to enter notes (about a topic) until finished; or review notes

Options:
  -c, --ch TEXT  string appended to the topic (default "> ")
  -s, --shell    Start an ipython shell to inspect the notes collection
  --help         Show this message and exit.

$ venv/bin/rh-shell --help
Usage: rh-shell [OPTIONS]

  Interactively select a Collection model and start ipython shell

Options:
  --help  Show this message and exit.
```

```python
>>> import redis_helper as rh
>>> collection = rh.Collection(..., index_fields='field1, field3')
>>> hash_id = collection.add(field1='', field2='', field3='', ...)
>>> collection.add(...)
>>> collection.add(...)
>>> collection.update(hash_id, field1='', field4='', ...)
>>> change_history = collection.old_data_for_hash_id(hash_id)
>>> data = collection.get(hash_id)
>>> some_data = collection.get(hash_id, 'field1, field3')
>>> results = collection.find(...)
>>> results2 = collection.find('field1:val, field3:val', ...)
>>> results3 = collection.find(..., get_fields='field2, field4')
>>> counts = collection.find(count=True, ...)
>>> top_indexed = collection.index_field_info()
>>> collection.delete(hash_id, ...)
```

## Basics - Part 1 (request logging demo)

[rh-basics-1 1:10]: https://asciinema.org/a/101422?t=1:10
[rh-basics-1 3:14]: https://asciinema.org/a/101422?t=3:14
[rh-basics-1 4:22]: https://asciinema.org/a/101422?t=4:22
[rh-basics-1 6:11]: https://asciinema.org/a/101422?t=6:11
[rh-basics-1 7:00]: https://asciinema.org/a/101422?t=7:00
[rh-basics-1 8:37]: https://asciinema.org/a/101422?t=8:37
[rh-basics-1 10:33]: https://asciinema.org/a/101422?t=10:33
[rh-basics-1 11:27]: https://asciinema.org/a/101422?t=11:27
[rh-basics-1 14:30]: https://asciinema.org/a/101422?t=14:30
[rh-basics-1 15:54]: https://asciinema.org/a/101422?t=15:54
[request_logs.py]: https://github.com/kenjyco/redis-helper/blob/master/examples/request_logs.py

[Demo][request logging demo] bookmarks:

- [1:10][rh-basics-1 1:10] is when the `ipython` session is started with
  `venv/bin/ipython -i request_logs.py`
- [3:14][rh-basics-1 3:14] is when a second `ipython` session is started (in a
  separate tmux pane) to simulate a steady stream of requests with
  `slow_trickle_requests(randomsleep=True, show=True)`
- [4:22][rh-basics-1 4:22] is when the `index_field_info` method is used to
  get the latest counts of top indexed items
- [6:11][rh-basics-1 6:11] is when `slow_trickle_requests(.001)` is run to
  simulate a large quick burst in traffic
- [7:00][rh-basics-1 7:00] is when multiple values are passed in the `since`
  argument of `find`... `request_logs.find(count=True, since='5:min, 1:min,
  30:sec')`
- [8:37][rh-basics-1 8:37] is when `get` and `get_by_position` methods are used
  with a variety of arguments to change the structure of what's returned
- [10:33][rh-basics-1 10:33] is when the `redis_helper.ADMIN_TIMEZONE` is
  changed at run time from `America/Chicago` to `Europe/London`
- [11:27][rh-basics-1 11:27] is when `find` is used with a variety of arguments
  to change the structure of what's returned
- [14:30][rh-basics-1 14:30] is when `find` is used with multiple search terms
  and multiple `since` values... `request_logs.find('host:dogs.com,
  uri:/breeds', count=True, since='5:min, 1:min, 10:sec')`
- [15:54][rh-basics-1 15:54] is when the `update` method is used to modify data
  and change history is retrieved with the `old_data_for_hash_id` method

The first demo walks through the following:

- creating a virtual environment, installing redis-helper, and downloading
  example files

    ```
    $ python3 -m venv venv
    $ venv/bin/pip3 install redis-helper ipython
    $ venv/bin/rh-download-examples
    $ cat ~/.config/redis-helper/settings.ini
    $ venv/bin/ipython -i request_logs.py
    ```
- using the sample `Collection` defined in [request_logs.py][] to
    - show values of some properties on a `Collection`
        - `redis_helper.Collection._base_key`
        - `redis_helper.Collection.now_pretty`
        - `redis_helper.Collection.now_utc_float`
        - `redis_helper.Collection.keyspace`
        - `redis_helper.Collection.size`
        - `redis_helper.Collection.first`
        - `redis_helper.Collection.last`
    - show values of some settings from `redis_helper`
        - `redis_helper.APP_ENV`
        - `redis_helper.REDIS_URL`
        - `redis_helper.REDIS`
        - `redis_helper.SETTINGS_FILE`
        - `redis_helper.ADMIN_TIMEZONE`
    - show output from some methods on a `Collection`
        - `redis_helper.Collection.index_field_info()`
        - `redis_helper.Collection.find()`
        - `redis_helper.Collection.find(count=True)`
        - `redis_helper.Collection.find(count=True, since='30:sec')`
        - `redis_helper.Collection.find(since='30:sec')`
        - `redis_helper.Collection.find(since='30:sec', admin_fmt=True)`
        - `redis_helper.Collection.find(count=True, since='5:min, 1:min, 30:sec')`
        - `redis_helper.Collection.find('index_field:value')`
        - `redis_helper.Collection.find('index_field:value', all_fields=True, limit=2)`
        - `redis_helper.Collection.find('index_field:value', all_fields=True, limit=2, admin_fmt=True, item_format='{_ts} -> {_id}')`
        - `redis_helper.Collection.find('index_field:value', get_fields='field1, field2', include_meta=False)`
        - `redis_helper.Collection.find('index_field1:value1, index_field2:value2', count=True)`
        - `redis_helper.Collection.find('index_field1:value1, index_field2:value2', count=True, since='5:min, 1:min, 10:sec')`
        - `redis_helper.Collection.get(hash_id)`
        - `redis_helper.Collection.get(hash_id, 'field1,field2,field3')`
        - `redis_helper.Collection.get(hash_id, include_meta=True)`
        - `redis_helper.Collection.get(hash_id, include_meta=True, fields='field1, field2')`
        - `redis_helper.Collection.get(hash_id, include_meta=True, item_format='{_ts} -> {_id}')`
        - `redis_helper.Collection.get_by_position(0)`
        - `redis_helper.Collection.get_by_position(0, include_meta=True, admin_fmt=True)`
        - `redis_helper.Collection.update(hash_id, field1='value1', field2='value2')`
        - `redis_helper.Collection.old_data_for_hash_id(hash_id)`

## Basics - Part 2 (urls demo, with unique field)

[urls.py]: https://github.com/kenjyco/redis-helper/blob/master/examples/urls.py

[Demo][urls demo] bookmarks:

- `TODO`

The second demo walks through the following:

- using the sample `Collection` defined in [urls.py][] to
    - `TODO`

## Settings, environments, testing, and debugging

To trigger a debugger session at a specific place in the [project code][],
insert the following, one line above where you want to inspect

```
import pdb; pdb.set_trace()
```

To start the debugger inside [test code][], use

```
pytest.set_trace()
```

- use `(l)ist` to list context lines
- use `(n)ext` to move on to the next statement
- use `(s)tep` to step into a function
- use `(c)ontinue` to continue to next break point (i.e. `set_trace()` lines in
  your code)
- use `sticky` to toggle sticky mode (to constantly show the currently executing
  code as you move through with the debugger)
- use `pp` to pretty print a variable or statement

If the redis server at `redis_url` (in the **test section** of
`~/.config/redis-server/settings.ini`) is not running or is not empty, redis
server tests will be skipped.

Use the `APP_ENV` environment variable to specify which section of the
`settings.ini` file your settings will be loaded from. Any settings in the
`default` section can be overwritten if explicity set in another section.

- if no `APP_ENV` is explicitly set, `dev` is assumed
- the `APP_ENV` setting is overwritten to be `test` no matter what was set when
  calling `py.test` tests
