   Note: as of redis-helper v0.4.0, version 3.0 of redis-py is in use,
   which has backwards incompatible changes withe redis-py 2.x. See
   https://github.com/redis/redis-py/tree/70ef9ec68f9163c86d4cace2941e2f0ae4ce8525#upgrading-from-redis-py-2x-to-30

redis-helper transforms Redis into a human-friendly data exploration and
analytics platform that optimizes for **cognitive flow**, **rapid
iteration**, and **interactive data exploration**. In the simplest use
case, you create an instance of ``redis_helper.Collection`` and specify
any optional fields to index when data is added to enable quick storage
and retrieval of Python dicts in Redis. You can filter through indexed
fields with flexible arguments to the ``find`` method and take advantage
of automatic timestamps for every entry added. There is also change
history for data that has been updated and automatic stats relating to
access/query patterns. When field validation is needed, regular
expressions may be defined via ``rx_{field}`` kwargs when creating the
collection instance.

At its core, redis-helper solves the mental burden of working with Redis
directly by providing a **single, powerful abstraction** that handles
complex operations behind intuitive, string-based interfaces. It’s built
for data scientists, analysts, and developers who need to **explore data
interactively**, **prototype quickly**, and **deploy confidently**
without sacrificing the performance and reliability that Redis provides.

See the `request logging demo <https://asciinema.org/a/101422?t=1:10>`__
and `urls
demo <https://asciinema.org/a/75kl95ty9vg2jl93pfz9fbs9q?t=1:00>`__ (with
``unique_field`` defined). The
`examples <https://github.com/kenjyco/redis-helper/tree/master/examples>`__
they reference are **short** and **easy to read**.

Install
-------

::

   pip install redis-helper

Dependency Incompatibility
~~~~~~~~~~~~~~~~~~~~~~~~~~

Note that when using hiredis v1.1.0, redis-py v5.0.8 (last release on
Python 3.7) is not compatible. Either use a newer version of hiredis or
redis-py 5.0.7 (on Python 3.7). Newer versions of redis-py (i.e. 5.1.0+
on Python 3.8 - 3.11) are compatible with hiredis v1.1.0.

Configuration
-------------

redis-helper uses a settings.ini file for Docker and connection
configuration:

.. code:: ini

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

..

   On first use, the default settings.ini file is copied to
   ``~/.config/redis-helper/settings.ini``

The library automatically starts Redis via Docker if no connection is
available, using these settings to configure container behavior,
persistence options, and connection parameters for both development and
testing environments.

Use the ``APP_ENV`` environment variable to specify which section of the
``settings.ini`` file your settings will be loaded from. Any settings in
the ``default`` section can be overwritten if explicity set in another
section. If no ``APP_ENV`` is explicitly set, ``dev`` is assumed.

QuickStart
----------

.. code:: python

   import redis_helper as rh

   # Create a collection for web request logs with validation
   ANALYTICS_REQUESTS = rh.Collection(
       'analytics', 'requests',
       unique_field='request_id',
       index_fields='status, method, host, user_id',
       json_fields='headers, response_data',
       rx_status=r'[1-5][0-9][0-9]',         # Validate HTTP status codes
       rx_method=r'(GET|POST|PUT|DELETE)',   # Validate HTTP methods
       insert_ts=True                        # Track creation vs modification time
   )

   # Add some sample data
   ANALYTICS_REQUESTS.add(
       request_id='req_123',
       method='GET',
       status=200,
       host='api.example.com',
       uri='/users/123',
       user_id='user_456',
       response_time=0.045,
       headers={'user-agent': 'curl/7.64.1', 'accept': '*/*'},
       response_data={'id': 123, 'name': 'John Doe', 'active': True}
   )

   ANALYTICS_REQUESTS.add(
       request_id='req_124',
       method='POST',
       status=400,
       host='api.example.com',
       uri='/users',
       user_id='user_789',
       response_time=0.012
   )

   ANALYTICS_REQUESTS.add(
       request_id='req_125',
       method='GET',
       status=200,
       host='web.example.com',
       uri='/dashboard',
       user_id='user_456',
       response_time=0.156
   )

   # Interactive exploration with powerful queries
   recent_errors = ANALYTICS_REQUESTS.find('status:400', since='1:hour')
   api_requests = ANALYTICS_REQUESTS.find('host:api.example.com, method:GET')

   # Multi-temporal analytics in a single query
   traffic_by_timeframe = ANALYTICS_REQUESTS.find('status:200', count=True, since='1:hour, 15:min, 5:min')
   # Returns: {'1:hour': 1234, '15:min': 345, '5:min': 89}

   # Human-readable formatting for reports
   print(ANALYTICS_REQUESTS.random(item_format='{method} {uri} -> {status} ({response_time}s) at {_ts}'))
   # Output: GET /users/123 -> 200 (0.045s) at 1642262202.123

   # Get data with admin timestamp formatting ("%a %m/%d/%Y %I:%M:%S %p")
   user_activity = ANALYTICS_REQUESTS.get('req_123', admin_fmt=True)
   print(user_activity['_ts'])  # Output: Mon 01/15/2024 02:30:22 PM

   # System introspection and monitoring
   print(f"Total requests: {ANALYTICS_REQUESTS.size}")
   print(f"Index distribution: {ANALYTICS_REQUESTS.index_field_info()}")
   print(f"Most accessed endpoints: {ANALYTICS_REQUESTS.get_stats()}")

Running this example gives you immediate access to sophisticated data
analytics capabilities with automatic timestamping, flexible querying,
built-in statistics, and human-optimized output formatting. The system
requires no configuration beyond basic field categorization and
automatically handles Redis connection management, key generation, and
data serialization.

Concepts
--------

Redis is a fast in-memory **data structure server**, where each stored
object is referenced by a key name. Objects in Redis correspond to one
of several basic types, each having their own set of specialized
commands to perform operations. The `redis Python
package <https://github.com/andymccurdy/redis-py>`__ provides the
`StrictRedis <https://redis-py.readthedocs.org/en/latest/#redis.StrictRedis>`__
class, which contains methods that correspond to all of the Redis server
commands, which redis-helper uses under the hood.

Tested for Python 3.5 - 3.13 against Redis 6 docker container.

When initializing Collection objects, you must specify the “namespace”
and “name” of the collection (which are used to create the internally
used ``_base_key`` property). All Redis keys associated with a
Collection will have a name pattern that starts with the ``_base_key``.

.. code:: python

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

-  a ``unique_field`` can be specified on a collection if items in the
   collection should not contain duplicate values for that particular
   field

   -  the ``unique_field`` cannot also be included in ``json_fields`` or
      ``pickle_fields``
   -  if you specify a ``unique_field``, that field must exist on each
      item you add to the collection

-  use ``index_fields`` to specify which fields you will want to filter
   on when using the ``find`` method

   -  the values for data fields being indexed MUST be simple strings or
      numbers
   -  the values for data fields being indexed SHOULD NOT be long
      strings, as the values themselves are part of the index keys

-  use ``json_fields`` to specify which fields should be JSON encoded
   before insertion to Redis
-  use ``rx_{field}`` to specify a regular expression for any field with
   strict rules for validation
-  use ``reference_fields`` to specify fields that reference the
   ``unique_field`` of another collection

   -  uses field–basekey combos

-  use ``pickle_fields`` to specify which fields should be pickled
   before insertion to Redis
-  set ``insert_ts=True`` to create an additional index to store insert
   times

   -  only do this if you are storing items that you are likely to
      update and also likely to want to know the original insert time

      -  each time an object is updated, the score associated with the
         ``hash_id`` (at the ``_ts_zset_key``) is updated to the current
         timestamp
      -  the score associated with the ``hash_id`` (at the
         ``_in_zset_key``) is never updated

Essentially, you can store a Python
`dict <https://docs.python.org/3/tutorial/datastructures.html#dictionaries>`__
in a Redis `hash <https://redis.io/topics/data-types#hashes>`__ and
index some of the fields in Redis
`sets <https://redis.io/topics/data-types#sets>`__. The collection’s
``_ts_zset_key`` is the Redis key name for the `sorted
set <https://redis.io/topics/data-types#sorted-sets>`__ containing the
``hash_id`` of every hash in the collection (with the ``score`` being a
``utc_float`` corresponding to the UTC time the ``hash_id`` was added or
modified).

-  if ``insert_ts=True`` was passed in when initializing the
   ``Collection`` (or sub-class), then the collection will also define
   ``self.in_zset_key`` to be the Redis key name for the sorted set (for
   ``hash_id`` and ``utc_float`` of insert time)

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

   -  the ``get_by_unique_value`` method is only useful if a
      ``unique_field`` was set on the Collection

The ``find`` method allows you to return data for items in the
collection that match some set of search criteria. Multiple search terms
(i.e. ``index_field:value`` pairs) maybe be passed in the ``terms``
parameter, as long as they are separated by one of ``,`` ``;`` ``|``.
Any fields specified in the ``get_fields`` parameter are passed along to
the ``get`` method (when the actual fetching takes place).

-  when using ``terms``, all terms that include the same field will be
   treatead like an “or” (union of related sets), then the intersection
   of different sets will be computed
-  see the Redis `set commands <https://redis.io/commands#set>`__ and
   `sorted set commands <https://redis.io/commands#sorted_set>`__

There are many options for specifying time ranges in the ``find`` method
including:

-  ``since`` and ``until`` when specifying ``num:unit`` strings
   (i.e. 15:seconds, 1.5:weeks, etc)
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
   urls.old_data_for_unique_value('redis-helper github')

The ``load_ref_data`` option on ``get``, ``get_by_unique_value``, or
``find`` methods allow you to load the referenced data object from the
other collection (where ``reference_fields`` are specified)

.. code:: python

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

Tip
---

There may be times where you want to use redis-helper (if it’s already
installed), but don’t want to make it an explicit requirement of your
project. In cases like this you can do the following:

::

   try:
       import redis_helper as rh
       from redis import ConnectionError as RedisConnectionError
   except (ImportError, ModuleNotFoundError):
       SomeCollection = None
   else:
       try:
           SomeCollection = rh.Collection(
               ...
           )
       except RedisConnectionError:
           SomeCollection = None

Then in whatever function, you can just do:

::

   def some_func():
       if SomeCollection is None:
           return

       # Do stuff with SomeCollection

Console Scripts
---------------

The ``rh-download-examples``, ``rh-download-scripts``, ``rh-notes``, and
``rh-shell`` scripts are provided.

::

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

API Overview
------------

Top-Level Functions
~~~~~~~~~~~~~~~~~~~

-  **``zshow(key, start=0, end=-1, desc=True, withscores=True)``** -
   Wrapper to Redis ZRANGE for debugging

   -  ``key`` (str): Redis sorted set key to examine
   -  ``start`` (int): Starting index
   -  ``end`` (int): Ending index
   -  ``desc`` (bool): Descending order
   -  ``withscores`` (bool): Include scores in output
   -  Returns: List of items from sorted set
   -  Internal calls: None

-  **``identity(x)``** - Return input value unmodified (null object
   pattern)

   -  ``x``: Any value to return unchanged
   -  Returns: The input value x
   -  Internal calls: None

-  **``start_docker(exception=False, show=False, force=False)``** -
   Start Redis Docker container using settings.ini configuration

   -  ``exception`` (bool): Raise exception if Docker has error response
   -  ``show`` (bool): Show Docker commands and output
   -  ``force`` (bool): Stop and remove container before recreating
   -  Returns: Boolean indicating success
   -  Internal calls: ``bh.tools.docker_redis_start()``

-  **``stop_docker(exception=False, show=False)``** - Stop Redis Docker
   container

   -  ``exception`` (bool): Raise exception if Docker has error response
   -  ``show`` (bool): Show Docker commands and output
   -  Returns: Boolean indicating success
   -  Internal calls: ``bh.tools.docker_stop()``

-  **``connect_to_server(url=REDIS_URL, attempt_docker=True, exception=False, show=False)``**
   - Connect to Redis server and set global REDIS variable

   -  ``url`` (str): Redis URL (redis://[:password@]host:port/db)
   -  ``attempt_docker`` (bool): Start Docker if connection fails
   -  ``exception`` (bool): Raise exception if unable to connect
   -  ``show`` (bool): Show Docker commands and output
   -  Returns: Tuple of (success_boolean, db_size)
   -  Internal calls: ``start_docker()``

Collection Creation and Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  **``Collection(namespace, name, unique_field='', index_fields='', json_fields='', pickle_fields='', expected_fields='', reference_fields='', insert_ts=False, list_name='', **kwargs)``**
   - Create and configure a new collection instance

   -  ``namespace`` (str): Top-level organization category (e.g.,
      ‘analytics’, ‘app’, ‘logs’)
   -  ``name`` (str): Specific collection identifier within namespace
   -  ``unique_field`` (str, optional): Field name that enforces
      uniqueness constraints
   -  ``index_fields`` (str, optional): Comma/semicolon/pipe-separated
      fields for fast lookups
   -  ``json_fields`` (str, optional): Fields that should be
      automatically JSON serialized/deserialized
   -  ``pickle_fields`` (str, optional): Fields for complex Python
      objects requiring pickle serialization
   -  ``expected_fields`` (str, optional): Fields that are likely to be
      used (for optimization)
   -  ``reference_fields`` (str, optional): Fields that reference unique
      values in other collections
   -  ``insert_ts`` (bool): Track creation time separately from
      modification time
   -  ``list_name`` (str, optional): Optional list name for specialized
      use cases
   -  ``**kwargs``: Additional configuration including ``rx_{field}``
      regex validation patterns
   -  Returns: Collection instance with all Redis keys and configuration
      established
   -  Internal calls: ``rh.connect_to_server()``,
      ``ih.make_var_name()``, ``ih.string_to_set()``,
      ``self.get_model()``

Data Manipulation
~~~~~~~~~~~~~~~~~

-  **``Collection.add(**data)``** - Add new item with automatic indexing
   and timestamping

   -  ``**data``: Arbitrary keyword arguments representing field-value
      pairs
   -  Returns: String hash ID for the created item
   -  Internal calls: ``self.validate()``, ``self.wait_for_unlock()``

-  **``Collection.get(hash_ids, fields='', include_meta=False, timestamp_formatter=rh.identity, ts_fmt=None, ts_tz=None, admin_fmt=False, item_format='', insert_ts=False, load_ref_data=False, update_get_stats=True)``**
   - Retrieve items with flexible formatting

   -  ``hash_ids`` (str or list): Single hash ID or list of hash IDs to
      retrieve
   -  ``fields`` (str): Comma-separated field names to retrieve (empty =
      all fields)
   -  ``include_meta`` (bool): Include system fields like ``_id`` and
      ``_ts``
   -  ``timestamp_formatter``: Function to format timestamp values
   -  ``ts_fmt`` (str): Timestamp format string
   -  ``ts_tz`` (str): Timezone for timestamp formatting
   -  ``admin_fmt`` (bool): Use admin formatting from settings
   -  ``item_format`` (str): Template string for custom output
      formatting
   -  ``insert_ts`` (bool): Use insertion time instead of modification
      time
   -  ``load_ref_data`` (bool): Resolve reference fields to actual
      referenced data
   -  ``update_get_stats`` (bool): Track access statistics for this
      operation
   -  Returns: Dictionary or list of dictionaries with requested data
   -  Internal calls: ``ih.string_to_list()``, ``ih.decode()``,
      ``ih.string_to_set()``,
      ``dh.get_timestamp_formatter_from_args()``, ``ih.from_string()``

-  **``Collection.update(hash_id, change_history=True, **data)``** -
   Modify existing item with change tracking

   -  ``hash_id`` (str): Target item identifier
   -  ``change_history`` (bool): Preserve previous values with
      timestamps
   -  ``**data``: Field-value pairs to update
   -  Returns: List of human-readable change descriptions
   -  Internal calls: ``self.validate()``, ``self.wait_for_unlock()``,
      ``self.get()``, ``ih.from_string()``

-  **``Collection.delete(hash_id, pipe=None)``** - Remove single item
   and clean up indexes

   -  ``hash_id`` (str): Item to remove
   -  ``pipe``: Optional Redis pipeline for batching
   -  Returns: Result of pipeline execution if pipe used, otherwise None
   -  Internal calls: ``self.wait_for_unlock()``, ``self.get()``

-  **``Collection.delete_many(*hash_ids)``** - Remove multiple items
   efficiently

   -  ``*hash_ids``: Variable number of hash IDs to delete
   -  Returns: Last result from pipeline execution
   -  Internal calls: ``self.wait_for_unlock()``, ``self.delete()``

-  **``Collection.delete_where(terms='', limit=None, desc=False, insert_ts=False)``**
   - Delete items matching query criteria

   -  ``terms`` (str): Query string like ‘field1:value1, field2:value2’
   -  ``limit`` (int): Maximum number of items to delete
   -  ``desc`` (bool): Process items in descending order
   -  ``insert_ts`` (bool): Use insertion timestamps for ordering
   -  Returns: Result from delete_many operation
   -  Internal calls: ``self.find()``, ``self.delete_many()``

-  **``Collection.delete_to(score=None, ts='', tz=None, insert_ts=False)``**
   - Delete items up to specified timestamp

   -  ``score`` (float): Timestamp score for deletion boundary
   -  ``ts`` (str): Human-readable timestamp (‘2017-01-01’, ‘2017-02-03
      7:15:00’)
   -  ``tz`` (str): Timezone for timestamp interpretation
   -  ``insert_ts`` (bool): Use insertion timestamps instead of
      modification timestamps
   -  Returns: Result from delete_many operation
   -  Internal calls: ``dh.date_string_to_utc_float_string()``,
      ``ih.decode()``, ``self.delete_many()``

Query Operations
~~~~~~~~~~~~~~~~

-  **``Collection.find(terms='', start=None, end=None, limit=20, desc=None, get_fields='', all_fields=False, count=False, ts_fmt=None, ts_tz=None, admin_fmt=False, start_ts='', end_ts='', since='', until='', include_meta=True, item_format='', insert_ts=False, load_ref_data=False, post_fetch_sort_key='', sort_key_default_val='')``**
   - Flexible search with temporal filtering

   -  ``terms`` (str): Query string like ‘field1:value1, field2:value2’
      with flexible delimiters
   -  ``start`` (int): Starting position for result slice
   -  ``end`` (int): Ending position for result slice
   -  ``limit`` (int): Maximum results to return
   -  ``desc`` (bool): Sort order (None for automatic inference, True
      for recent-first)
   -  ``get_fields`` (str): Specific fields to retrieve
   -  ``all_fields`` (bool): Include all fields regardless of
      configuration
   -  ``count`` (bool): Return counts instead of data
   -  ``ts_fmt`` (str): Timestamp format string
   -  ``ts_tz`` (str): Timezone for timestamp formatting
   -  ``admin_fmt`` (bool): Use admin formatting from settings
   -  ``start_ts`` (str): Absolute start timestamp
   -  ``end_ts`` (str): Absolute end timestamp
   -  ``since`` (str): Relative time expressions (‘1:hour’,
      ‘30:minutes’, ‘5:min, 1:min, 30:sec’)
   -  ``until`` (str): Relative end time expression
   -  ``include_meta`` (bool): Include system metadata fields
   -  ``item_format`` (str): Custom output formatting template
   -  ``insert_ts`` (bool): Use insertion time instead of modification
      time
   -  ``load_ref_data`` (bool): Resolve reference fields
   -  ``post_fetch_sort_key`` (str): Field to sort results by after
      retrieval
   -  ``sort_key_default_val``: Default value for missing sort keys
   -  Returns: List of matching items or dictionary of counts by time
      range
   -  Internal calls: ``dh.get_time_ranges_and_args()``,
      ``dh.get_timestamp_formatter_from_args()``, ``self.get()``,
      ``ih.decode()``

-  **``Collection.random(terms='', start=None, end=None, ts_fmt=None, ts_tz=None, admin_fmt=False, start_ts='', end_ts='', since='', until='', **get_kwargs)``**
   - Get random sample with same filtering options as find

   -  ``terms`` (str): Query string like ‘field1:value1, field2:value2’
      with flexible delimiters
   -  ``start`` (int): Starting position for result slice
   -  ``end`` (int): Ending position for result slice
   -  ``ts_fmt`` (str): Timestamp format string
   -  ``ts_tz`` (str): Timezone for timestamp formatting
   -  ``admin_fmt`` (bool): Use admin formatting from settings
   -  ``start_ts`` (str): Absolute start timestamp
   -  ``end_ts`` (str): Absolute end timestamp
   -  ``since`` (str): Relative time expressions (‘1:hour’,
      ‘30:minutes’, ‘5:min, 1:min, 30:sec’)
   -  ``until`` (str): Relative end time expression
   -  ``**get_kwargs``: Additional parameters accepted by the get()
      method
   -  Returns: Single random item matching criteria
   -  Internal calls: ``dh.get_time_ranges_and_args()``,
      ``dh.get_timestamp_formatter_from_args()``, ``self.get()``,
      ``self.get_by_position()``

Specific Access Methods
~~~~~~~~~~~~~~~~~~~~~~~

-  **``Collection.get_by_unique_value(unique_val, fields='', include_meta=False, timestamp_formatter=rh.identity, ts_fmt=None, ts_tz=None, admin_fmt=False, item_format='', insert_ts=False, load_ref_data=False, update_get_stats=True)``**
   - Retrieve item by unique field value

   -  ``unique_val``: Value to search for in the unique field
   -  All other parameters same as ``get()`` method
   -  Returns: Dictionary with item data or empty dict if not found
   -  Internal calls: ``self.get_hash_id_for_unique_value()``,
      ``self.get()``

-  **``Collection.get_by_position(pos, **kwargs)``** - Get item by
   position (most recent first by default)

   -  ``pos`` (int): Position index (0 = most recent)
   -  ``**kwargs``: All parameters accepted by ``get()`` method
   -  Returns: Dictionary with item data
   -  Internal calls: ``self.get()``

-  **``Collection.get_by_slice(start=None, stop=None, **kwargs)``** -
   Get slice of items by position

   -  ``start`` (int): Starting position
   -  ``stop`` (int): Ending position
   -  ``**kwargs``: All parameters accepted by ``get()`` method
   -  Returns: List of dictionaries
   -  Internal calls: ``self.get()``

-  **``Collection.get_hash_id_for_unique_value(unique_val)``** - Get
   hash ID for unique field value

   -  ``unique_val``: Value to look up
   -  Returns: Hash ID string or None if not found
   -  Internal calls: None

Collection Management
~~~~~~~~~~~~~~~~~~~~~

-  **``Collection.get_model(cls, base_key=None, init_args=None)``**
   (classmethod) - Reconstruct Collection instance from Redis state

   -  ``base_key`` (str): Redis base key for the collection
   -  ``init_args`` (str): Initialization arguments string
   -  Returns: Collection instance
   -  Internal calls: ``ih.decode()``

-  **``Collection.select_models(cls, named=False)``** (classmethod) -
   Interactive collection chooser

   -  ``named`` (bool): Return dictionary with collection names as keys
   -  Returns: Selected Collection instance(s)
   -  Internal calls: ``cls.init_stats()``, ``ih.make_selections()``,
      ``cls.get_model()``

-  **``Collection.select_model(cls)``** (classmethod) - Select single
   collection interactively

   -  Returns: Single Collection instance
   -  Internal calls: ``cls.select_models()``

-  **``Collection.select_and_modify(menu_item_format='', action='update', prompt='', update_fields='', **find_kwargs)``**
   - Interactive bulk operations

   -  ``menu_item_format`` (str): Template for displaying items in
      selection menu
   -  ``action`` (str): Operation type (‘update’ or ‘delete’)
   -  ``prompt`` (str): Custom prompt for user selection
   -  ``update_fields`` (str): Fields to modify during update operations
   -  ``**find_kwargs``: All parameters accepted by ``find()`` method
   -  Returns: Results of selected operations
   -  Internal calls: ``ih.string_to_set()``,
      ``ih.get_keys_in_string()``, ``self.find()``,
      ``ih.make_selections()``, ``ih.user_input()``, ``self.update()``,
      ``self.delete()``

Validation and Maintenance
~~~~~~~~~~~~~~~~~~~~~~~~~~

-  **``Collection.validate(**data)``** - Validate fields against
   configured regex patterns

   -  ``**data``: Field-value pairs to validate
   -  Returns: List of validation error tuples (field, value, pattern)
   -  Internal calls: None

-  **``Collection.reindex()``** - Rebuild all search indexes from
   current data

   -  Returns: None
   -  Internal calls: ``self.wait_for_unlock()``, ``ih.decode()``,
      ``rh.zshow()``, ``self.get()``

-  **``Collection.clear_keyspace()``** - Remove all data and indexes for
   this collection

   -  Returns: None
   -  Internal calls: None

System Properties and Introspection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  **``Collection.namespace``** (property) - Collection’s namespace

   -  Returns: String namespace value
   -  Internal calls: None

-  **``Collection.name``** (property) - Collection’s name

   -  Returns: String name value
   -  Internal calls: None

-  **``Collection.var_name``** (property) - Variable-safe name for
   collection

   -  Returns: String variable name
   -  Internal calls: None

-  **``Collection.size``** (property) - Current number of items in
   collection

   -  Returns: Integer count
   -  Internal calls: None

-  **``Collection.last``** (property) - Most recently modified item

   -  Returns: Dictionary with item data
   -  Internal calls: ``self.get_by_position()``

-  **``Collection.last_admin``** (property) - Most recent item with
   admin timestamp formatting

   -  Returns: Dictionary with formatted timestamps
   -  Internal calls: ``self.get_by_position()``

-  **``Collection.first``** (property) - Oldest item in collection

   -  Returns: Dictionary with item data
   -  Internal calls: ``self.get_by_position()``

-  **``Collection.first_admin``** (property) - Oldest item with admin
   timestamp formatting

   -  Returns: Dictionary with formatted timestamps
   -  Internal calls: ``self.get_by_position()``

-  **``Collection.last_update``** (property) - Timestamp of last
   collection modification

   -  Returns: Float timestamp
   -  Internal calls: ``ih.decode()``

-  **``Collection.last_update_admin``** (property) - Formatted timestamp
   of last modification

   -  Returns: Human-readable timestamp string
   -  Internal calls: ``self.last_update``, ``dh.utc_float_to_pretty()``

-  **``Collection.now_pretty``** (property) - Current timestamp in admin
   format

   -  Returns: Human-readable current timestamp
   -  Internal calls: ``dh.utc_now_pretty()``

-  **``Collection.now_utc_float_string``** (property) - Current
   timestamp as string

   -  Returns: Current UTC timestamp as string
   -  Internal calls: ``dh.utc_now_float_string()``

-  **``Collection.info``** (property) - Complete system state and
   configuration summary

   -  Returns: Formatted string with initialization args, size, last
      update, keyspace structure, and index statistics
   -  Internal calls: ``self.size``, ``self.last_update_admin``,
      ``self.keyspace``, ``self.index_field_info()``,
      ``self.get_stats()``, ``self.get()``

-  **``Collection.keyspace``** (property) - Redis key structure for
   debugging and monitoring

   -  Returns: Sorted list of (key_name, key_type) tuples showing all
      Redis keys used by this collection
   -  Internal calls: ``ih.decode()``

-  **``Collection.is_locked``** (property) - Check if collection is
   currently locked

   -  Returns: Boolean lock status
   -  Internal calls: ``ih.from_string()``, ``ih.decode()``

Statistics and Analysis
~~~~~~~~~~~~~~~~~~~~~~~

-  **``Collection.get_stats(limit=5)``** - Access pattern analysis for
   items and fields accessed by get() method

   -  ``limit`` (int): Number of top items to return in statistics
   -  Returns: Dictionary with keys: ``counts`` (access frequency),
      ``fields`` (field access patterns), ``timestamps`` (access timing)
   -  Internal calls: ``dh.utc_float_to_pretty()``, ``ih.decode()``

-  **``Collection.find_stats(limit=5)``** - Summary info about temporary
   sets created during find calls

   -  ``limit`` (int): Number of top search patterns to return
   -  Returns: Dictionary with keys: ``counts``, ``sizes``,
      ``timestamps``
   -  Internal calls: ``ih.decode()``, ``rh.zshow()``,
      ``dh.utc_float_to_pretty()``

-  **``Collection.init_stats(cls, limit=5)``** (classmethod) -
   Collection creation statistics across all collections

   -  ``limit`` (int): Number of entries to return
   -  Returns: Dictionary with collection initialization patterns
   -  Internal calls: ``dh.utc_float_to_pretty()``, ``ih.decode()``

-  **``Collection.index_field_info(limit=10)``** - Data distribution
   analysis for indexed fields

   -  ``limit`` (int): Number of top values per index to return
   -  Returns: List of 2-item tuples with field names and their top
      values/counts
   -  Internal calls: ``self.size``, ``ih.decode()``, ``rh.zshow()``

-  **``Collection.top_values_for_index(index_name, limit=10)``** - Most
   common values for specific index

   -  ``index_name`` (str): Name of indexed field to analyze
   -  ``limit`` (int): Number of top values to return
   -  Returns: List of (value, count) tuples
   -  Internal calls: ``self.recent_unique_values()``

Historical Data Access
~~~~~~~~~~~~~~~~~~~~~~

-  **``Collection.old_data_for_hash_id(hash_id)``** - Change history for
   specific item

   -  ``hash_id`` (str): Item to get history for
   -  Returns: List of dictionaries with change history including
      timestamps, fields, and values
   -  Internal calls: ``ih.decode()``, ``dh.utc_float_to_pretty()``

-  **``Collection.old_data_for_unique_value(unique_val)``** - Change
   history by unique field value

   -  ``unique_val``: Unique field value to get history for
   -  Returns: List of change history dictionaries
   -  Internal calls: ``self.get_hash_id_for_unique_value()``,
      ``self.old_data_for_hash_id()``

-  **``Collection.recent_unique_values(limit=10)``** - Most recently
   used unique field values

   -  ``limit`` (int): Number of values to return
   -  Returns: List of unique values ordered by recent use
   -  Internal calls: ``ih.decode()``

-  **``Collection.all_unique_values()``** - All unique field values in
   collection

   -  Returns: List of all unique field values
   -  Internal calls: ``self.recent_unique_values()``

Utility Methods
~~~~~~~~~~~~~~~

-  **``Collection.wait_for_unlock(sleeptime=0.5)``** - Wait for
   collection to become unlocked

   -  ``sleeptime`` (float): Seconds to sleep between lock checks
   -  Returns: Total time slept
   -  Internal calls: ``self.is_locked``

-  **``Collection.clear_find_stats()``** - Reset query statistics

   -  Returns: None
   -  Internal calls: None

-  **``Collection.clear_get_stats()``** - Reset access statistics

   -  Returns: None
   -  Internal calls: None

-  **``Collection.clear_init_stats()``** - Reset initialization
   statistics

   -  Returns: None
   -  Internal calls: None

-  **``Collection.clear_all_collection_locks(cls)``** (classmethod) -
   Remove all collection locks (emergency use)

   -  Returns: None
   -  Internal calls: ``cls.init_stats()``

-  **``Collection.report_all(cls)``** (classmethod) - Generate report of
   all collections

   -  Returns: None (prints report)
   -  Internal calls: None

Container Protocol Support
~~~~~~~~~~~~~~~~~~~~~~~~~~

The Collection class implements Python’s container protocols for
intuitive access:

-  ``collection[0]`` - Get item by position (most recent first)
-  ``collection['hash_id']`` - Get item by direct hash ID
-  ``collection['unique_value']`` - Get item by unique field value
   (falls back to random sample)
-  ``collection[0:10]`` - Get slice of items
-  ``len(collection)`` - Get total item count
-  ``for item in collection:`` - Iterate through all items
