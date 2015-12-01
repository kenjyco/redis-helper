__all__ = ['REDIS', 'next_object_id', 'index_hash_field', 'add_dict',
           'getall_dicts'
]

import time
from functools import partial
from redis import StrictRedis, ResponseError

REDIS = StrictRedis()


def next_object_id(key, sep=':', start=1000, redis_client=None):
    """Return the next 'key' to be used for new redis object; increment 'next_id'

    - key: the key name
    - sep: delimiter character used to separate parts of the key
    - start: initial numerical id to be appended to key
    """
    redis_client = redis_client or REDIS
    k = '{}{}next_id'.format(key, sep)
    redis_client.setnx(k, start)
    _id = redis_client.get(k)
    redis_client.incr(k)
    return '{}{}{}'.format(key, sep, _id)

def index_hash_field(hash_id, field, value, prefix='', sep=':', use_time=False,
                     score=0, redis_client=None):
    """Add 'hash_id' to a set (or sorted set), for indexing a field of the hash

    If 'use_time' or 'score' are provided, then add to a sorted set. Otherwise,
    add to a normal set.

    - hash_id: the key name of the hash
    - field: name of the field in the hash to index
    - value: value of the field for the hash
    - prefix: a string that the generated index key name should start with
    - sep: delimiter character used to separate parts of hash_id
    - use_time: if True, use current epoch time as score and add to sorted set
    - score: if non-zero, use as score and add to sorted set
    """
    redis_client = redis_client or REDIS
    if prefix:
        k = '{}{}idx{}{}{}{}'.format(prefix, sep, sep, field, sep, value)
    else:
        k = 'idx{}{}{}{}'.format(sep, field, sep, value)

    if use_time:
        redis_client.zadd(k, time.time(), hash_id)
    elif score:
        redis_client.zadd(k, score, hash_id)
    else:
        redis_client.sadd(k, hash_id)
    return k

def add_dict(hash_id, somedict, indexfields=[], prefix='', sep=':',
             use_time=False, score=0, redis_client=None):
    """Add a python dictionary to redis (or update it), at a specified key

    Return a 2-item tuple containing the `hash_id` and a list of `index_ids`
    (returned by the `index_hash_field` function).

    - hash_id: redis key for the hash to create/update
    - somedict: a python dictionary object (flat is better, i.e scalar values)
    - indexfields: list of fields in the newly created redis hash to be indexed

    Options passed to `index_hash_field`:

    - prefix: a string that the generated index key name should start with
    - sep: delimiter character used to separate parts of hash_id
    - use_time: if True, use current epoch time as score and add to sorted set
    - score: if non-zero, use as score and add to sorted set

    add_dict('somekey', {'a': 3, 'z': 9, 'y': 2, 'b': 4}, indexfields=['z', 'a'])
    """
    redis_client = redis_client or REDIS
    redis_client.hmset(hash_id, somedict)
    index_ids = []
    for field in indexfields:
        idx_id = index_hash_field(hash_id, field, somedict.get(field, ''),
                         prefix=prefix, sep=sep, use_time=use_time, score=score,
                         redis_client=redis_client)
        index_ids.append(idx_id)
    return (hash_id, index_ids)

def getall_dicts(rediskey_or_list, redis_client=None):
    """Return a list of dicts (from a redis object containing redis hash_ids)

    - rediskey_or_list: redis key name to an object containing hash_ids, or a
      Python list/tuple/set of hash_ids
    """
    redis_client = redis_client or REDIS
    if redis_client.exists(rediskey_or_list):
        obj_type = REDIS.type(rediskey_or_list)
        if obj_type == 'zset':
            cmd = partial(redis_client.zrange, rediskey_or_list, 0, -1)
        elif obj_type == 'list':
            cmd = partial(redis_client.lrange, rediskey_or_list, 0, -1)
        elif obj_type == 'set':
            cmd = partial(redis_client.smembers, rediskey_or_list)
        else:
            print '{} is a redis object of type {}'.format(
                repr(rediskey_or_list), repr(obj_type)
            )
            return

        try:
            return [redis_client.hgetall(hash_id) for hash_id in cmd()]
        except ResponseError as e:
            if 'WRONGTYPE' in repr(e):
                # One or more of the keys was for a non-hash redis object
                dicts = []
                badkeys = []
                for hash_id in cmd():
                    try:
                        dicts.append(redis_client.hgetall(hash_id))
                    except:
                        badkeys.append((redis_client.type(hash_id), hash_id))
                msg = 'Some keys were for non-hash redis objects!!\n{}'
                print msg.format(repr(badkeys))
                return dicts
            else:
                print repr(e)
                return

    if type(rediskey_or_list) in (list, tuple, set):
        return [
            redis_client.hgetall(hash_id)
            for hash_id in rediskey_or_list
        ]
    else:
        msg = '{} is not a redis object or a Python list/tuple/set!!\nType is {}'
        print msg.format(repr(rediskey_or_list), repr(type(rediskey_or_list)))
