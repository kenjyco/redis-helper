Redis Helper
============

> Helper functions to store/retrieve redis objects.

## Install

```
% pip install git+git://github.com/kenjyco/redis_helper.git
```

## Usage

#### Storing dictionary objects

```
from redis_helper import next_object_id, add_dict

somedict = {'a': 3, 'z': 9, 'y': 2, 'b': 4}
hash_id = next_object_id('thing:mydict')
add_dict(hash_id, somedict, indexfields=['z', 'a'], prefix='thing',
         use_time=True)
```

- Use `next_object_id` to get a new Redis key name
- Use `add_dict` (with the new key name) to add a dictionary object to Redis

#### Retrieving dictionary objects

```
from redis_helper import getall_dicts

index = 'thing:idx:z:9'
dicts = getall_dicts(index)
```

- Use `getall_dicts` to get a list of dictionary objects at a particular index
  (which contains IDs of Redis hash objects)

## Background

[dict]: https://docs.python.org/2/tutorial/datastructures.html#dictionaries
[hash]: http://redis.io/commands#hash
[Redis]: http://redis.io/topics/data-types-intro
[redis-py]: https://github.com/andymccurdy/redis-py
[StrictRedis]: https://redis-py.readthedocs.org/en/latest/#redis.StrictRedis
[helpers]: https://github.com/kenjyco/redis_helper/blob/master/redis_helper/__init__.py

A [Python dictionary][dict] is a very useful **container** for grouping facts
about some particular entity/object. Dictionaries have **keys** that map to
**values**, so if we want to retrieve a particular value stored in a dictionary,
we can access it through its key. The dictionary itself is accessed by its
**variable name**.

[Redis][] is a **data structure server** (among other things). It is great for
storing various types of objects that can be accessed between different programs
and processes. When your program stops running, objects that you have stored in
Redis will remain. To retreive an object from Redis, you must access it through
its **key name** (kind of like a Python variable name).

A [Redis hash][hash] is most similar to a Python dictionary. A "key" in a Python
dictionary is analogous to a "field" in a Redis hash (since "key" means
something different in Redis). The [redis-py][] library provides the
[StrictRedis][] class, which contain methods that correspond to all of the Redis
server commands.

> The [helper functions][helpers] all expect an instance of `StrictRedis` to be
> passed in as the `redis_client`.
