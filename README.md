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

## More examples (in ipython)

#### Example 1

Get some strings that represent Redis key names

```
In [1]: from redis_helper import *

In [2]: hash_id1 = next_object_id('misc:somedicts'); hash_id1
Out[2]: 'misc:somedicts:1000'

In [3]: hash_id2 = next_object_id('misc:somedicts'); hash_id2
Out[3]: 'misc:somedicts:1001'

In [4]: hash_id3 = next_object_id('misc:somedicts'); hash_id3
Out[4]: 'misc:somedicts:1002'

In [5]: hash_id4 = next_object_id('misc:somedicts'); hash_id4
Out[5]: 'misc:somedicts:1003'

In [6]: hash_id5 = next_object_id('misc:somedicts'); hash_id5
Out[6]: 'misc:somedicts:1004'
```

Add some dictionaries at each key name, indexing on one common field

```
In [7]: add_dict(hash_id1, {'color': 'green', 'size': 'large', 'rating': 'good'}, indexfields=['color'], prefix='misc', use_time=True)
Out[7]: ('misc:somedicts:1000', ['misc:idx:color:green'])

In [8]: add_dict(hash_id2, {'color': 'brown', 'size': 'large', 'rating': 'great'}, indexfields=['color'], prefix='misc', use_time=True)
Out[8]: ('misc:somedicts:1001', ['misc:idx:color:brown'])

In [9]: add_dict(hash_id3, {'color': 'orange', 'size': 'extra large', 'rating': 'fantastic'}, indexfields=['color'], prefix='misc', use_time=True)
Out[9]: ('misc:somedicts:1002', ['misc:idx:color:orange'])

In [10]: add_dict(hash_id4, {'color': 'orange', 'texture': 'smooth', 'rating': 'fantastic'}, indexfields=['color'], prefix='misc', use_time=True)
Out[10]: ('misc:somedicts:1003', ['misc:idx:color:orange'])

In [12]: add_dict(hash_id5, {'color': 'orange', 'reflective': False, 'shape': 'cylinder', 'condition': 'fair'}, indexfields=['color'], prefix='misc', use_time=True)
Out[12]: ('misc:somedicts:1004', ['misc:idx:color:orange'])
```

Investigate a particular index

```
In [13]: REDIS.type('misc:idx:color:orange')
Out[13]: 'zset'

In [14]: REDIS.zcard('misc:idx:color:orange')
Out[14]: 3

In [15]: REDIS.zrange('misc:idx:color:orange', 0, -1, withscores=True)
Out[15]:
[('misc:somedicts:1002', 1449217060.374798),
 ('misc:somedicts:1003', 1449218335.224642),
 ('misc:somedicts:1004', 1449218363.657641)]

In [16]: getall_dicts('misc:idx:color:orange')
Out[16]:
[{'color': 'orange', 'rating': 'fantastic', 'size': 'extra large'},
 {'color': 'orange', 'rating': 'fantastic', 'texture': 'smooth'},
 {'color': 'orange',
  'condition': 'fair',
  'reflective': 'False',
  'shape': 'cylinder'}]
```
