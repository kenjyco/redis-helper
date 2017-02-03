Use ``redis_helper.Collection`` to **define a data model in a single
statement**. Then, use the ``add``, ``get``, ``update``, ``delete``, and
``find`` methods to power **real-time dashboards**, super-charge **event
logging**, and speed up **information retrieval** across system
components.

The first time that ``redis_helper`` is imported, the sample
`settings.ini <https://github.com/kenjyco/redis-helper/blob/master/redis_helper/settings.ini>`__
file will be copied to the ``~/.config/redis-helper`` directory.

Install latest tag/release of `redis-helper from pypi <https://pypi.python.org/pypi/redis-helper>`__
----------------------------------------------------------------------------------------------------

::

    % pip install redis-helper

Install latest commit on master of `redis-helper from github <https://github.com/kenjyco/redis-helper>`__
---------------------------------------------------------------------------------------------------------

::

    % pip install git+git://github.com/kenjyco/redis-helper

Intro
-----

`Redis <http://redis.io/topics/data-types-intro>`__ is a fast in-memory
**data structure server**, where each stored object is referenced by a
key name. Objects in Redis correspond to one of several basic types,
each having their own set of specialized commands to perform operations.
The `redis Python package <https://github.com/andymccurdy/redis-py>`__
provides the
`StrictRedis <https://redis-py.readthedocs.org/en/latest/#redis.StrictRedis>`__
class, which contains methods that correspond to all of the Redis server
commands.

When initializing Collection objects, you must specify the "namespace"
and "name" of the collection (which are used to create the internally
used ``_base_key`` property). All Redis keys associated with a
Collection will have a name pattern that starts with the ``_base_key``.

.. code:: python

    import redis_helper as rh


    request_logs = rh.Collection(
        'log',
        'request',
        index_fields='status,uri,host',
        json_fields='request,response,headers'
    )

    urls = rh.Collection(
        'web',
        'url',
        unique_field='name',
        index_fields='domain,_type'
    )

-  a ``unique_field`` can be specified on a collection if items in the
   collection should not contain duplicate values for that particular
   field

   -  if you specify a ``unique_field``, that field must exist on each
      item you add to the collection

-  use ``index_fields`` to specify which fields you will want to filter
   on when using the ``find`` method

   -  the values for data fields being indexed MUST be simple strings or
      numbers
   -  the values for data fields being indexed SHOULD NOT be long
      strings, as the values themselves are part of the index keys

-  use ``json_fields`` to specify which fields should be JSON encoded
   before insertion to Redis (using the very fast
   `ujson <https://pypi.python.org/pypi/ujson>`__ library)
-  use ``pickle_fields`` to specify which fields should be pickled
   before insertion to Redis

Essentially, you can store a Python
`dict <https://docs.python.org/3/tutorial/datastructures.html#dictionaries>`__
in a Redis `hash <https://redis.io/topics/data-types#hashes>`__ and
index some of the fields in Redis
`sets <https://redis.io/topics/data-types#sets>`__. The collection's
``_ts_zset_key`` is the Redis key name for the `sorted
set <https://redis.io/topics/data-types#sorted-sets>`__ containing the
``hash_id`` of every hash in the collection (with the ``score`` being a
``utc_float`` corresponding to the UTC time the ``hash_id`` was added or
modified).

.. code:: python

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

The ``get`` method is a wrapper to `hash
commands <http://redis.io/commands#hash>`__ ``hget``, ``hmget``, or
``hgetall``. The actual hash command that gets called is determined by
the number of fields requested.

-  a Python dict is typically returned from ``get``
-  if ``item_format`` is specified, a string will be returned matching
   that format instead

.. code:: python

    request_logs.get('log:request:1')
    request_logs.get('log:request:1', 'host,status')
    request_logs.get('log:request:1', item_format='{status} for {host}{uri}')
    request_logs.get_by_position(0, item_format='{status} for {host}{uri}')
    urls.get_by_position(-1, 'domain,url')
    urls.get_by_unique_value('redis-helper github', item_format='{url} points to a {_type}')

-  the ``get_by_position`` and ``get_by_unique_value`` methods are
   wrappers to ``get``

The ``find`` method allows you to return data for items in the
collection that match some set of search criteria. Multiple search terms
(i.e. ``index_field:value`` pairs) maybe be passed in the ``terms``
parameter, as long as they are separated by one of ``,`` ``;`` ``|``.
Any fields specified in the ``get_fields`` parameter are passed along to
the ``get`` method (when the actual fetching takes place).

-  when using ``terms``, all terms that include the same field will be
   treatead like an "or" (union of related sets), then the intersection
   of different sets will be computed
-  see the Redis `set commands <https://redis.io/commands#set>`__ and
   `sorted set commands <https://redis.io/commands#sorted_set>`__

There are many options for specifying time ranges in the ``find`` method
including:

-  ``since`` and ``until`` when specifying ``num:unit`` strings (i.e.
   15:seconds, 1.5:weeks, etc)
-  ``start_ts`` and ``end_ts`` when specifying timestamps with a form
   between ``YYYY`` and ``YYYY-MM-DD HH:MM:SS.f``
-  ``start`` and ``end`` when specifying a ``utc_float``
-  for ``since``, ``until``, ``start_ts``, and ``end_ts``, multiple
   values may be passed in the string, as long as they are separated by
   one of ``,`` ``;`` ``|``.

   -  when multiple time ranges are specified, the ``find`` method will
      determine all reasonable combinations and return a result-set per
      combination (instead of returning a list of items, returns a dict
      of list of items)

If ``count=True`` is specified, the number of results matching the
search criteria are returned instead of the actual results

-  if there are multiple time ranges specified, counts will be returned
   for each combination

.. code:: python

    request_logs.find('status:400, host:blah.net', get_fields='uri,error')
    request_logs.find(since='1:hr, 30:min', until='15:min, 5:min')
    request_logs.find(count=True, since='1:hr, 30:min', until='15:min, 5:min')
    urls.find(count=True, since='1:hr, 30:min, 10:min, 5:min, 1:min')
    urls.find(start_ts='2017-02-03', end_ts='2017-02-03 7:15:00')
    urls.find(start_ts='2017-02-03', item_format='{_ts} -> {_id}')

The ``update`` method allows you to change values for some fields
(modifying the ``unique_field``, when it is specified, is not allowed).

-  every time a field is modified for a particular ``hash_id``, the
   previous value and score (timestamp) are stored in a Redis hash
-  the ``old_data_for_hash_id`` or ``old_data_for_unique_value`` methods
   can be used to retrieve the history of all changes for a ``hash_id``

.. code:: python

    urls.update('web:url:1', _type='fancy', notes='this is a fancy url')
    urls.old_data_for_hash_id('web:url:1')
    urls.old_data_for_unique_value('redis-helper github'

Local development setup
-----------------------

::

    % git clone https://github.com/kenjyco/redis-helper
    % cd redis-helper
    % ./dev-setup.bash

The
`dev-setup.bash <https://github.com/kenjyco/redis-helper/blob/master/dev-setup.bash>`__
script will create a virtual environment in the ``./venv`` directory
with extra dependencies (ipython, pdbpp, pytest), then copy
``settings.ini`` to the ``~/.config/redis-helper`` directory.

Running tests in development setup
----------------------------------

The
`setup.cfg <https://github.com/kenjyco/redis-helper/blob/master/setup.cfg>`__
file contains the options for ``py.test``, currently ``-vsx -rs --pdb``.

The ``-vsx -rs --pdb`` options will run tests in a verbose manner and
output the reason why tests were skipped (if any were skipped). If there
are any failing tests, ``py.test`` will stop on the first failure and
drop you into a `pdb++ <https://pypi.python.org/pypi/pdbpp/>`__ debugger
session.

See the `debugging
section <https://github.com/kenjyco/redis-helper#settings-environments-testing-and-debugging>`__
of the README for tips on using the debugger and setting breakpoints (in
the actual `project
code <https://github.com/kenjyco/redis-helper/tree/master/redis_helper>`__,
or in the `test
code <https://github.com/kenjyco/redis-helper/tree/master/tests>`__).

::

    % venv/bin/py.test

or

::

    % venv/bin/python3 setup.py test

    Note: This option requires ``setuptools`` to be installed.

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

`Demo <https://asciinema.org/a/101422?autoplay=1>`__ bookmarks:

-  `1:10 <https://asciinema.org/a/101422?t=1:10>`__ is when the
   ``ipython`` session is started with
   ``venv/bin/ipython -i request_logs.py``
-  `10:33 <https://asciinema.org/a/101422?t=10:33>`__ is an example of
   changing the ``redis_helper.ADMIN_TIMEZONE`` at run time

The first demo walks through the following:

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

   -  show values of some properties on a ``Collection``

      -  ``redis_helper.Collection._base_key``
      -  ``redis_helper.Collection.now_pretty``
      -  ``redis_helper.Collection.now_utc_float``
      -  ``redis_helper.Collection.keyspace``
      -  ``redis_helper.Collection.size``
      -  ``redis_helper.Collection.first``
      -  ``redis_helper.Collection.last``

   -  show values of some settings from ``redis_helper``

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
      -  ``redis_helper.Collection.find('index_field1:value1, index_field2:value2', count=True)``
      -  ``redis_helper.Collection.find('index_field1:value1, index_field2:value2', count=True, since='5:min, 1:min, 10:sec')``
      -  ``redis_helper.Collection.get(hash_id)``
      -  ``redis_helper.Collection.get(hash_id, 'field1,field2,field3')``
      -  ``redis_helper.Collection.get(hash_id, include_meta=True)``
      -  ``redis_helper.Collection.get(hash_id, include_meta=True, fields='field1,field2')``
      -  ``redis_helper.Collection.get(hash_id, include_meta=True, item_format='{_ts} -> {_id}')``
      -  ``redis_helper.Collection.get_by_position(0)``
      -  ``redis_helper.Collection.get_by_position(0, include_meta=True, admin_fmt=True)``
      -  ``redis_helper.Collection.update(hash_id, field1='value1', field2='value2')``
      -  ``redis_helper.Collection.old_data_for_hash_id(hash_id)``

Settings, environments, testing, and debugging
----------------------------------------------

To trigger a debugger session at a specific place in the `project
code <https://github.com/kenjyco/redis-helper/tree/master/redis_helper>`__,
insert the following, one line above where you want to inspect

::

    import pdb; pdb.set_trace()

To start the debugger inside `test
code <https://github.com/kenjyco/redis-helper/tree/master/tests>`__, use

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
