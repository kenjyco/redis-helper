Redis Helper
============

> Easily store, index, and modify Python dicts in Redis (with flexible
> searching).

[rh pypi]: https://pypi.python.org/pypi/redis-helper
[rh github]: https://github.com/kenjyco/redis_helper
[settings]: https://github.com/kenjyco/redis_helper/blob/master/settings.ini
[example1]: https://github.com/kenjyco/redis_helper/blob/master/examples/request_logs.py
[dev-setup]: https://github.com/kenjyco/redis_helper/blob/master/dev-setup.bash

# Installation Methods

When using `pip` to install, the sample [settings.ini][settings] and
[request_logs.py][example1] example will be copied to the
`~/.config/redis-helper` directory.

#### Latest released version of [redis-helper from pypi][rh pypi]

```
% pip install redis-helper
```

#### Latest commit on master of [redis_helper from github][rh github]

```
% pip install git+git://github.com/kenjyco/redis_helper
```

#### Dev setup

The [dev-setup.bash][dev-setup] script will

- create a virtual environment in the `./venv` directory with extra dependencies
  (ipython, pdbpp, pytest)
- copy `settings.ini` to the `~/.config/redis-helper` directory

```
% git clone https://github.com/kenjyco/redis_helper
% cd redis_helper
% python3 setup.py test     # optional
% ./dev-setup.bash
```

Tests can be run via **`venv/bin/py.test tests`** and install can be tested (if
`setup.py` was modified) via **`venv/bin/python3 setup.py install`**.

> Note: any of the above commands that involves `setup.py` requires setuptools
> (i.e. `sudo apt-get install python3-setuptools`)

# Usage

```python
>>> import redis_helper as rh
>>> collection = rh.RedThing(..., index_fields='field1,field3')
>>> hash_id = collection.add(field1='', field2='', field3='', ...)
>>> collection.add(...)
>>> collection.add(...)
>>> collection.update(hash_id, field1='', field4='', ...)
>>> change_history = collection.old_data_for_hash_id(hash_id)
>>> data = collection.get(hash_id)
>>> some_data = collection.get(hash_id, 'field1,field3')
>>> results = collection.find(...)
>>> results2 = collection.find('field1:val,field3:val', ...)
>>> results3 = collection.find(..., get_fields='field2,field4')
>>> counts = collection.find(count=True, ...)
>>> top_indexed = collection.index_field_info()
>>> collection.delete(hash_id, ...)
```

# Background

[dict]: https://docs.python.org/3/tutorial/datastructures.html#dictionaries
[hash]: http://redis.io/commands#hash
[Redis]: http://redis.io/topics/data-types-intro
[redis-py]: https://github.com/andymccurdy/redis-py
[StrictRedis]: https://redis-py.readthedocs.org/en/latest/#redis.StrictRedis

A [Python dictionary][dict] is a very useful **container** for grouping facts
about some particular entity. Dictionaries have **keys** that map to
**values** (so if we want to retrieve a particular value stored in a dictionary,
we can access it through its key). The dictionary itself is accessed by its
**variable name**.

[Redis][] is a **data structure server** (among other things). It is great for
storing various types of objects that can be accessed between different programs
and processes. When your program stops running, objects that you have stored in
Redis will remain. To retreive an object from Redis, you must access it through
its **key name** (kind of like a Python variable name). The
[redis Python package][redis-py] provides the [StrictRedis][] class, which
contains methods that correspond to all of the Redis server commands.

A [Redis hash][hash] is most similar to a Python dictionary. A "key" in a Python
dictionary is analogous to a "field" in a Redis hash (since "key" means
something different in Redis).
