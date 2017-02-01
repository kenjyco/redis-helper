The first time that ``redis_helper`` is imported, the sample
`settings.ini <https://github.com/kenjyco/redis-helper/blob/master/settings.ini>`__
file will be copied to the ``~/.config/redis-helper`` directory.

Install latest tag of `redis-helper from pypi <https://pypi.python.org/pypi/redis-helper>`__
--------------------------------------------------------------------------------------------

::

    % pip install redis-helper

Install latest commit on master of `redis-helper from github <https://github.com/kenjyco/redis-helper>`__
---------------------------------------------------------------------------------------------------------

::

    % pip install git+git://github.com/kenjyco/redis-helper

Local development setup
-----------------------

::

    % git clone https://github.com/kenjyco/redis-helper
    % cd redis-helper
    % python3 setup.py test     # optional, requires 'setuptools'
    % ./dev-setup.bash

The
`dev-setup.bash <https://github.com/kenjyco/redis-helper/blob/master/dev-setup.bash>`__
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
    >>> collection = rh.Collection(..., index_fields='field1,field3')
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

Basics - Part 1
---------------

The first demo walks through the following

-  creating a virtual environment, installing redis-helper, and
   downloading example files

   ::

       $ python3 -m venv venv
       $ venv/bin/pip3 install redis-helper ipython
       $ venv/bin/rh-download-examples
       $ cat ~/.config/redis-helper/settings.ini
       $ venv/bin/ipython -i request_logs.py

-  using the sample ``Collection`` defined in
   `request\_logs.py <https://github.com/kenjyco/redis-helper/blob/master/examples/request_logs.py>`__
   to

   -  show values of properties on a ``Collection``

      -  ``redis_helper.Collection._base_key``
      -  ``redis_helper.Collection.now_pretty``
      -  ``redis_helper.Collection.now_utc_float``
      -  ``redis_helper.Collection.keyspace``
      -  ``redis_helper.Collection.size``
      -  ``redis_helper.Collection.first``
      -  ``redis_helper.Collection.last``

   -  show values of settings from ``redis_helper``

      -  ``redis_helper.APP_ENV``
      -  ``redis_helper.REDIS_URL``
      -  ``redis_helper.REDIS``
      -  ``redis_helper.SETTINGS_FILE``
      -  ``redis_helper.ADMIN_TIMEZONE``

   -  show output from some methods on a ``Collection``

      -  ``redis_helper.Collection.index_field_info()``
      -  ``redis_helper.Collection.find()``
      -  ``redis_helper.Collection.find(count=True)``
      -  ``redis_helper.Collection.find(count=True, since='30:sec')``
      -  ``redis_helper.Collection.find(since='30:sec')``
      -  ``redis_helper.Collection.find(since='30:sec', admin_fmt=True)``
      -  ``redis_helper.Collection.find(count=True, since='5:min, 1:min, 30:sec')``
      -  ``redis_helper.Collection.find('index_field:value')``
      -  ``redis_helper.Collection.find('index_field:value', all_fields=True, limit=2)``
      -  ``redis_helper.Collection.find('index_field:value', all_fields=True, limit=2, admin_fmt=True, item_format='{_ts} -> {_id}')``
      -  ``redis_helper.Collection.find('index_field:value', get_fields='field1,field2', include_meta=False)``
      -  ``redis_helper.Collection.find('index_field2:value1, index_field2:value2', count=True)``
      -  ``redis_helper.Collection.find('index_field2:value1, index_field2:value2', count=True, since='5:min, 1:min, 10:sec')``
      -  ``redis_helper.Collection.get(hash_id)``
      -  ``redis_helper.Collection.get(hash_id, 'field1,field2,field3')``
      -  ``redis_helper.Collection.get(hash_id, include_meta=True)``
      -  ``redis_helper.Collection.get(hash_id, include_meta=True, fields='field1,field2')``
      -  ``redis_helper.Collection.get(hash_id, include_meta=True, item_format='{_ts} -> {_id}')``
      -  ``redis_helper.Collection.get_by_position(0)``
      -  ``redis_helper.Collection.get_by_position(0, include_meta=True, admin_fmt=True)``
      -  ``redis_helper.Collection.update(hash_id, field1='value1', field2='value2')``
      -  ``redis_helper.Collection.old_data_for_hash_id(hash_id)``

    Note: Jump to the `10:33
    mark <https://asciinema.org/a/101422?t=10:33>`__ to see example of
    changing the ``ADMIN_TIMEZONE`` (in interpreter, instead of in
    settings.ini)

|basics-1|

Settings, environments, testing, and debugging
----------------------------------------------

When using ``venv/bin/py.test -vsx -rs --pdb tests``, tests will stop
running on the first failure and drop you into a
`pdb++ <https://pypi.python.org/pypi/pdbpp/>`__ debugger session.

To trigger a debugger session at a specific place in the code, insert
the following, one line above where you want to inspect

::

    import pdb; pdb.set_trace()

To start the debugger inside test code, use

::

    pytest.set_trace()

-  use ``(l)ist`` to list context lines
-  use ``(n)ext`` to move on to the next statement
-  use ``(s)tep`` to step into a function
-  use ``(c)ontinue`` to continue to next break point (i.e.
   ``set_trace()`` lines in your code)
-  use ``sticky`` to toggle sticky mode (to constantly show the
   currently executing code as you move through with the debugger)
-  use ``pp`` to pretty print a variable or statement

If the redis server at ``redis_url`` (in the **test section** of
``~/.config/redis-server/settings.ini``) is not running or is not empty,
redis server tests will be skipped.

Use the ``APP_ENV`` environment variable to specify which section of the
``settings.ini`` file your settings will be loaded from. Any settings in
the ``default`` section can be overwritten if explicity set in another
section.

-  if no ``APP_ENV`` is explicitly set, ``dev`` is assumed
-  the ``APP_ENV`` setting is overwritten to be ``test`` no matter what
   was set when calling ``py.test`` tests

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

.. |basics-1| image:: https://asciinema.org/a/101422.png
   :target: https://asciinema.org/a/101422?t=1:10
