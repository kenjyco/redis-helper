Redis Helper
============

    Easily store, index, and modify Python dicts in Redis (with flexible
    searching).

Install
-------

::

    % pip install redis-helper

Place a copy of the
`settings.ini <https://raw.githubusercontent.com/kenjyco/redis_helper/master/settings.ini.sample>`__
file in either ``/etc/redis-helper/`` or ``~/.config/redis-helper/`` and
modify.

Usage
-----

.. code:: python

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

    Note: this is only a small usage sample. Several ``RedThing``
    methods have many parameters.

Test running
------------

::

    % git clone https://github.com/kenjyco/redis_helper
    % cd redis_helper
    % python3 setup.py test

    Note: requires setuptools (i.e.
    ``sudo apt-get install python3-setuptools``)

Background
----------

A `Python
dictionary <https://docs.python.org/3/tutorial/datastructures.html#dictionaries>`__
is a very useful **container** for grouping facts about some particular
entity. Dictionaries have **keys** that map to **values** (so if we want
to retrieve a particular value stored in a dictionary, we can access it
through its key). The dictionary itself is accessed by its **variable
name**.

`Redis <http://redis.io/topics/data-types-intro>`__ is a **data
structure server** (among other things). It is great for storing various
types of objects that can be accessed between different programs and
processes. When your program stops running, objects that you have stored
in Redis will remain. To retreive an object from Redis, you must access
it through its **key name** (kind of like a Python variable name).

A `Redis hash <http://redis.io/commands#hash>`__ is most similar to a
Python dictionary. A "key" in a Python dictionary is analogous to a
"field" in a Redis hash (since "key" means something different in
Redis). The `redis-py <https://github.com/andymccurdy/redis-py>`__
library provides the
`StrictRedis <https://redis-py.readthedocs.org/en/latest/#redis.StrictRedis>`__
class, which contain methods that correspond to all of the Redis server
commands.
