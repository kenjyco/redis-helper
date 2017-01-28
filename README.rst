When using ``pip`` to install, the sample
`settings.ini <https://github.com/kenjyco/redis_helper/blob/master/settings.ini>`__
and
`request\_logs.py <https://github.com/kenjyco/redis_helper/blob/master/examples/request_logs.py>`__
example will be copied to the ``~/.config/redis-helper`` directory.

Install latest tag of `redis-helper from pypi <https://pypi.python.org/pypi/redis-helper>`__
--------------------------------------------------------------------------------------------

::

    % pip install redis-helper

Install latest commit on master of `redis\_helper from github <https://github.com/kenjyco/redis_helper>`__
----------------------------------------------------------------------------------------------------------

::

    % pip install git+git://github.com/kenjyco/redis_helper

Local development setup
-----------------------

::

    % git clone https://github.com/kenjyco/redis_helper
    % cd redis_helper
    % python3 setup.py test     # optional, requires 'setuptools'
    % ./dev-setup.bash

The
`dev-setup.bash <https://github.com/kenjyco/redis_helper/blob/master/dev-setup.bash>`__
script will create a virtual environment in the ``./venv`` directory
with extra dependencies (ipython, pdbpp, pytest), then copy
``settings.ini`` to the ``~/.config/redis-helper`` directory.

Running tests in development setup
----------------------------------

::

    % venv/bin/py.test tests

or

::

    % venv/bin/py.test -vsx -rs --pdb tests

The ``py.test`` options will run tests in a verbose manner and output
the reason why tests were skipped (if any were skipped). If there are
any failing tests, ``py.test`` will stop on the first failure and drop
you into the debugger.

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
it through its **key name** (kind of like a Python variable name). The
`redis Python package <https://github.com/andymccurdy/redis-py>`__
provides the
`StrictRedis <https://redis-py.readthedocs.org/en/latest/#redis.StrictRedis>`__
class, which contains methods that correspond to all of the Redis server
commands.

A `Redis hash <http://redis.io/commands#hash>`__ is most similar to a
Python dictionary. A "key" in a Python dictionary is analogous to a
"field" in a Redis hash (since "key" means something different in
Redis).
