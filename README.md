Redis Helper
============

> Helper functions to store/retrieve redis objects.

## Install

```
% pip install git+git://github.com/kenjyco/redis_helper.git
```

## Usage

> TODO

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
