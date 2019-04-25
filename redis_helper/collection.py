import pickle
import ujson
import random
import re
import warnings
import redis_helper as rh
import input_helper as ih
import dt_helper as dh
from time import sleep
from collections import defaultdict, OrderedDict
from functools import partial
from itertools import chain
from io import StringIO
from pprint import pprint
from redis import ResponseError


META_FIELDS = {'_id', '_ts'}
_CURLY_MATCHER = ih.matcher.CurlyMatcher()


class Collection(object):
    """Store, index, and modify Python dicts in Redis with flexible searching

    Create an instance of `redis_helper.Collection` and use the 'add', 'get',
    'update', 'delete', and 'find' methods to

    - quickly store/retrieve/modify Python dicts in Redis
    - filter through indexed fields with simple/flexible find arguments
    - gather count metrics or actual data at a variety of time ranges at once
    """
    def __init__(self, namespace, name, unique_field='', index_fields='',
                 json_fields='', pickle_fields='', expected_fields='',
                 reference_fields='',
                 insert_ts=False, list_name='', **kwargs):
        """Pass in namespace and name

        - unique_field: name of the optional unique field
        - index_fields: string of fields that should be indexed
        - json_fields: string of fields that should be serialized as JSON
        - pickle_fields: string of fields with complex/arbitrary structure
        - expected_fields: string of fields that are likely to be used
        - reference_fields: string of field--base_key combos for fields that
          correspond to the unique_field of another collection
        - insert_ts: if True, use an additional index for insert times
        - list_name: if provided _______________
        - kwargs: any other kwargs passed in
            - rx_{field}: a regular expression used to validate the field
              before add/update

        Separate fields in strings by any of , ; |
        """
        self._namespace = namespace
        self._name = name
        self._var_name = ih.make_var_name('{}_{}'.format(namespace, name))
        self._unique_field = unique_field
        index_fields_set = ih.string_to_set(index_fields)
        self._json_fields = ih.string_to_set(json_fields)
        self._pickle_fields = ih.string_to_set(pickle_fields)
        self._expected_fields = ih.string_to_set(expected_fields)
        self._reference_fields = ih.string_to_set(reference_fields)
        self._insert_ts = insert_ts
        self._list_name = list_name
        self.field_rx_dict = {}
        self.field_reference_dict = {}

        u = set([unique_field])
        invalid = (
            index_fields_set.intersection(self._json_fields)
            .union(index_fields_set.intersection(self._pickle_fields))
            .union(index_fields_set.intersection(u))
            .union(self._json_fields.intersection(self._pickle_fields))
            .union(self._json_fields.intersection(u))
            .union(self._pickle_fields.intersection(u))
        )
        assert invalid == set(), 'field(s) used in too many places: {}'.format(invalid)
        invalid = (
            META_FIELDS.intersection(
                index_fields_set.union(self._json_fields)
                .union(self._pickle_fields)
                .union(u)
            )
        )
        assert invalid == set(), '{} not allowed to be saved or updated'.format(invalid)

        self._base_key = self._make_key(namespace, name)
        self._index_base_keys = {
            index_field: self._make_key(self._base_key, index_field)
            for index_field in index_fields_set
        }
        self._next_id_string_key = self._make_key(self._base_key, '_next_id')
        self._ts_zset_key = self._make_key(self._base_key, '_ts')
        self._id_zset_key = self._make_key(self._base_key, '_id')
        self._in_zset_key = self._make_key(self._base_key, '_in')
        self._get_id_stats_hash_key = self._make_key(self._base_key, '_get_id_stats')
        self._get_field_stats_hash_key = self._make_key(self._base_key, '_get_field_stats')
        self._lock_string_key = self._make_key(self._base_key, '_LOCK')
        self._find_base_key = self._make_key(self._base_key, '_find')
        self._find_next_id_string_key = self._make_key(self._find_base_key, '_next_id')
        self._find_stats_hash_key = self._make_key(self._find_base_key, '_stats')
        self._find_searches_zset_key = self._make_key(self._find_base_key, '_searches')

        ref_errors = []
        for f in self._reference_fields:
            field, collection_name = f.rsplit('--', 1)
            model = self.get_model(collection_name)
            if model is None:
                ref_errors.append(
                    'Collection {} does not exist'.format(repr(collection_name))
                )
                continue
            if not model._unique_field:
                ref_errors.append(
                    'Collection {} does not have a unique_field'.format(repr(collection_name))
                )
                continue
            self.field_reference_dict[field] = model
        if ref_errors:
            warnings.warn('Reference field errors: ' + repr(ref_errors))

        _parts = [
            '({}, {}'.format(repr(namespace), repr(name)),
            'unique_field={}'.format(repr(unique_field)) if unique_field else '',
            'index_fields={}'.format(repr(index_fields)) if index_fields else '',
            'json_fields={}'.format(repr(json_fields)) if json_fields else '',
            'pickle_fields={}'.format(repr(pickle_fields)) if pickle_fields else '',
            'expected_fields={}'.format(repr(expected_fields)) if expected_fields else '',
            'reference_fields={}'.format(repr(reference_fields)) if reference_fields else '',
            'insert_ts={}'.format(repr(insert_ts)) if insert_ts else '',
            'list_name={}'.format(repr(list_name)) if list_name else '',
        ]
        for k, v in sorted(kwargs.items()):
            if k.startswith('rx_'):
                self.field_rx_dict[k[3:]] = re.compile('^{}$'.format(v))
            _parts.append('{}={}'.format(k, repr(v)))

        self._init_args = ''.join([
            self.__class__.__name__,
            ', '.join([p for p in _parts if p is not '']),
            ')'
        ])
        pipe = rh.REDIS.pipeline()
        pipe.hset('_REDIS_HELPER_COLLECTION', self._base_key + '--last_args', self._init_args)
        pipe.hset('_REDIS_HELPER_COLLECTION', self._base_key + '--last_size', self.size)
        pipe.execute()

        if self.__class__.__name__ != 'Collection':
            item = rh.REDIS.get(self._init_args)
            if not item:
                rh.REDIS.set(self._init_args, pickle.dumps(self))

    def __repr__(self):
        return self._init_args

    def __len__(self):
        return self.size

    def __getitem__(self, i):
        _type_i = type(i)
        if _type_i == int:
            return self.get_by_position(i, include_meta=True)
        elif _type_i == str and i.startswith(self._base_key):
            return self.get(i, include_meta=True)
        elif _type_i == str and self._unique_field and i:
            val = self.get_by_unique_value(i, include_meta=True)
            if not val:
                return self.random(i, include_meta=True)
            return val
        elif _type_i == str and i:
            return self.random(i, include_meta=True)
        elif _type_i == slice:
            return self.get_by_slice(i.start, i.stop, include_meta=True)
        else:
            return {}

    def __iter__(self):
        self._i = 0
        return self

    def __next__(self):
        i = self._i
        if i < self.size:
            self._i += 1
            return self.get_by_position(i, include_meta=True)
        else:
            raise StopIteration

    def _make_key(self, *parts):
        """Join the string parts together, separated by colon(:)"""
        return ':'.join([str(part) for part in parts])

    def _get_next_key(self, next_id_string_key, base_key=None):
        """Get the next key to use and increment next_id_string_key"""
        if base_key is None:
            base_key = ':'.join(next_id_string_key.split(':')[:-1])
        pipe = rh.REDIS.pipeline()
        pipe.setnx(next_id_string_key, 1)
        pipe.get(next_id_string_key)
        pipe.incr(next_id_string_key)
        result = pipe.execute()
        return self._make_key(base_key, int(result[1]))

    def _get_next_find_key(self):
        return self._get_next_key(self._find_next_id_string_key, self._find_base_key)

    def _lock(self):
        """Lock the collection from being modified"""
        rh.REDIS.set(self._lock_string_key, 'True')

    def _unlock(self):
        """Unlock the collection and allow modifications"""
        rh.REDIS.set(self._lock_string_key, 'False')

    @property
    def is_locked(self):
        """Return True if the collection is locked"""
        return True == ih.from_string(ih.decode(rh.REDIS.get(self._lock_string_key)))

    def wait_for_unlock(self, sleeptime=.5):
        """Don't return until the collection is unlocked; total sleep time returned

        - sleeptime: amount of time to sleep between checking the lock
        """
        total_sleep = 0
        while self.is_locked == True:
            total_sleep += sleeptime
            sleep(sleeptime)
        return total_sleep

    def add(self, **data):
        """Add all fields and values in data to the collection

        If self._unique_field is a non-empty string, that field must be provided
        in the data and there must not be an item in the collection with the
        same value for that field
        """
        for mf in META_FIELDS:
            assert mf not in data, (
                '{} is a meta field that cannot be saved or updated'.format(repr(mf))
            )
        if self._unique_field:
            unique_val = data.get(self._unique_field)
            assert unique_val is not None, (
                'unique field {} is not in data'.format(repr(self._unique_field))
            )
            score = rh.REDIS.zscore(self._id_zset_key, unique_val)
            assert score is None, (
                '{}={} already exists'.format(self._unique_field, repr(unique_val))
            )
        errors = self.validate(**data)
        if errors:
            raise Exception('Validation errors: ' + repr(errors))

        self.wait_for_unlock()
        self._lock()
        now = self.now_utc_float
        key = self._get_next_key(self._next_id_string_key, self._base_key)
        id_num = int(key.split(':')[-1])
        for field in self._json_fields:
            val = data.get(field)
            if val is not None:
                data[field] = ujson.dumps(val)
        for field in self._pickle_fields:
            val = data.get(field)
            if val is not None:
                data[field] = pickle.dumps(val)
        pipe = rh.REDIS.pipeline()
        pipe.hset('_REDIS_HELPER_COLLECTION', self._base_key + '--last_update', self.now_utc_float)
        pipe.hset('_REDIS_HELPER_COLLECTION', self._base_key + '--last_size', self.size + 1)
        if self._unique_field:
            pipe.zadd(self._id_zset_key, id_num, unique_val)
        pipe.zadd(self._ts_zset_key, now, key)
        if self._insert_ts:
            pipe.zadd(self._in_zset_key, now, key)
        pipe.hmset(key, data)
        for index_field, base_key in self._index_base_keys.items():
            key_name = self._make_key(base_key, data.get(index_field))
            pipe.sadd(key_name, key)
            pipe.zincrby(base_key, str(data.get(index_field)), 1)
        pipe.execute()
        self._unlock()
        return key

    def get(self, hash_ids, fields='', include_meta=False,
            timestamp_formatter=rh.identity, ts_fmt=None, ts_tz=None,
            admin_fmt=False, item_format='', insert_ts=False,
            load_ref_data=False, update_get_stats=True):
        """Wrapper to rh.REDIS.hget/hmget/hgetall

        - hash_ids: string of hash_ids to get data for separated by any of , ; |
        - fields: string of field names to get separated by any of , ; |
        - include_meta: if True include attributes _id and _ts
        - timestamp_formatter: a callable to apply to the _ts timestamp
        - ts_fmt: strftime format for the returned timestamps (_ts field)
        - ts_tz: a timezone to convert the timestamp to before formatting
        - admin_fmt: if True, use format and timezone defined in settings file
        - item_format: format string for each item (return a string instead of
          a dict)
        - insert_ts: if True and include_meta is True, return the insert time
          for the '_ts' meta field (instead of modify time)
        - load_ref_data: if True, also load info from any collections specified
          in init reference_fields that also appears in fields
        - update_get_stats: if True update access count and last access time
          for each hash_id and update field access counts for each field in
          'fields'
        """
        hash_ids = ih.string_to_list(ih.decode(hash_ids))
        if admin_fmt or ts_fmt or ts_tz:
            include_meta = True
        if item_format:
            # Ensure that all fields specified in item_format are fetched
            fields_in_string = set(_CURLY_MATCHER(item_format).get('curly_group_list', []))
            fields = fields_in_string - META_FIELDS
            if META_FIELDS.intersection(fields_in_string):
                include_meta = True
        else:
            fields = ih.string_to_set(fields)
        num_fields = len(fields)
        if timestamp_formatter == rh.identity and include_meta:
            if ts_fmt or ts_tz or admin_fmt:
                timestamp_formatter = dh.get_timestamp_formatter_from_args(
                    ts_fmt=ts_fmt,
                    ts_tz=ts_tz,
                    admin_fmt=admin_fmt
                )
        if include_meta:
            key = self._ts_zset_key if not insert_ts else self._in_zset_key

        # Define the _get_data func based on number of fields requested
        if num_fields == 1:
            field = fields.pop()
            _get_data = lambda hash_id: {field: rh.REDIS.hget(hash_id, field)}
        elif num_fields > 1:
            _get_data = lambda hash_id: dict(zip(fields, rh.REDIS.hmget(hash_id, *fields)))
        else:
            _get_data = lambda hash_id: {
                ih.decode(k): v
                for k, v in rh.REDIS.hgetall(hash_id).items()
            }

        results = []
        if update_get_stats:
            # Start creating the 'pipe' for adding get_*_stats
            pipe = rh.REDIS.pipeline()

        for hash_id in hash_ids:
            try:
                data = _get_data(hash_id)
            except ResponseError:
                data = {}

            if update_get_stats:
                pipe.hincrby(self._get_id_stats_hash_key, hash_id + '--count', 1)
                pipe.hset(self._get_id_stats_hash_key, hash_id + '--last_access', self.now_utc_float)

            for field in data.keys():
                if update_get_stats:
                    pipe.hincrby(self._get_field_stats_hash_key, field, 1)
                if field in self._json_fields:
                    try:
                        data[field] = ujson.loads(data[field])
                    except (ValueError, TypeError):
                        data[field] = ih.decode((data[field]))
                elif field in self._pickle_fields:
                    data[field] = pickle.loads(data[field])
                else:
                    val = ih.decode(data[field])
                    data[field] = ih.from_string(val) if val is not None else None
            if include_meta:
                data['_id'] = ih.decode(hash_id)
                data['_ts'] = timestamp_formatter(
                    rh.REDIS.zscore(key, hash_id)
                )
                if update_get_stats:
                    for field in META_FIELDS:
                        pipe.hincrby(self._get_field_stats_hash_key, field, 1)

            if item_format:
                results.append(item_format.format(**data))
            else:
                if load_ref_data:
                    for field, collection in self.field_reference_dict.items():
                        if field in data:
                            _ref_field_data = collection[data[field]]
                            if _ref_field_data:
                                data[field] = _ref_field_data
                results.append(data)

        if update_get_stats:
            pipe.execute()

        if len(results) == 1:
            return results[0]
        return results


    def get_hash_id_for_unique_value(self, unique_val):
        """Return the hash_id of the object that has unique_val in _unique_field"""
        if self._unique_field:
            score = rh.REDIS.zscore(self._id_zset_key, unique_val)
            if score:
                return self._make_key(self._base_key, int(score))

    def get_by_unique_value(self, unique_val, fields='', include_meta=False,
                            timestamp_formatter=rh.identity, ts_fmt=None,
                            ts_tz=None, admin_fmt=False, item_format='',
                            load_ref_data=False):
        """Wrapper to self.get

        - fields: string of field names to get separated by any of , ; |
        - include_meta: if True include attributes _id and _ts
        - timestamp_formatter: a callable to apply to the _ts timestamp
        - ts_fmt: strftime format for the returned timestamps (_ts field)
        - ts_tz: a timezone to convert the timestamp to before formatting
        - admin_fmt: if True, use format and timezone defined in settings file
        - item_format: format string for each item (return a string instead of
          a dict)
        - load_ref_data: if True, also load info from any collections specified
          in init reference_fields that also appears in fields
        """
        hash_id = self.get_hash_id_for_unique_value(unique_val)
        data = {}
        if hash_id:
            data = self.get(
                hash_id,
                fields=fields,
                include_meta=include_meta,
                timestamp_formatter=timestamp_formatter,
                ts_fmt=ts_fmt,
                ts_tz=ts_tz,
                admin_fmt=admin_fmt,
                item_format=item_format,
                load_ref_data=load_ref_data
            )
        return data

    def get_by_position(self, pos, **kwargs):
        """Wrapper to self.get

        - insert_ts: if True, use position of insert time instead of modify time
        """
        data = {}
        if 'update_get_stats' not in kwargs:
            kwargs['update_get_stats'] = False
        insert_ts = kwargs.get('insert_ts', False)
        key = self._ts_zset_key if not insert_ts else self._in_zset_key
        x = rh.REDIS.zrange(key, pos, pos, withscores=True)
        if x:
            hash_id, ts = x[0]
            data = self.get(hash_id, **kwargs)
        return data

    def get_by_slice(self, start=None, stop=None, **kwargs):
        """Wrapper to self.get

        - start: start index position
        - stop: stop index position
        - insert_ts: if True, use position of insert time instead of modify time
        """
        _start = start or 0
        _stop = stop or -1
        if stop is not None:
            _stop -= 1
        if 'update_get_stats' not in kwargs:
            kwargs['update_get_stats'] = False
        insert_ts = kwargs.get('insert_ts', False)
        key = self._ts_zset_key if not insert_ts else self._in_zset_key
        return [
            self.get(hash_id, **kwargs)
            for hash_id, ts in rh.REDIS.zrange(key, _start, _stop, withscores=True)
        ]

    def random(self, terms='', start=None, end=None, ts_fmt=None, ts_tz=None,
               admin_fmt=False, start_ts='', end_ts='', since='', until='',
               **get_kwargs):
        """Wrapper to self.get via self.get_by_position (or a pseudo self.find)

        - terms: string of 'index_field:value' pairs separated by any of , ; |
            - if provided, return a random result from the result set
        - start: utc_float
        - end: utc_float
        - ts_fmt: strftime format for the returned timestamps (_ts field)
        - ts_tz: a timezone to convert the timestamp to before formatting
        - admin_fmt: if True, use format and timezone defined in settings file
        - start_ts: timestamps with form between YYYY and YYYY-MM-DD HH:MM:SS.f
          (in the timezone specified in ts_tz or dh.ADMIN_TIMEZONE)
        - end_ts: timestamps with form between YYYY and YYYY-MM-DD HH:MM:SS.f
          (in the timezone specified in ts_tz or dh.ADMIN_TIMEZONE)
        - since: 'num:unit' strings (i.e. 15:seconds, 1.5:weeks, etc)
        - until: 'num:unit' strings (i.e. 15:seconds, 1.5:weeks, etc)
        - get_kwargs: dict of keyword arguments to pass to self.get
        """
        item = {}
        timestamp_formatter = dh.get_timestamp_formatter_from_args(
            ts_fmt=ts_fmt,
            ts_tz=ts_tz,
            admin_fmt=admin_fmt
        )
        if 'update_get_stats' not in get_kwargs:
            get_kwargs['update_get_stats'] = False
        get_kwargs['timestamp_formatter'] = timestamp_formatter
        if admin_fmt or ts_fmt or ts_tz:
            get_kwargs['include_meta'] = True
        if terms:
            insert_ts = get_kwargs.get('insert_ts', False)
            now = self.now_utc_float_string
            result_key, result_key_is_tmp = self._redis_zset_from_terms(terms, insert_ts)
            time_ranges = dh.get_time_ranges_and_args(
                tz=ts_tz,
                now=now,
                start=start,
                end=end,
                start_ts=start_ts,
                end_ts=end_ts,
                since=since,
                until=until
            )

            # Select a single time_range, assuming that the longest key name
            # is the "most specific" (even thought that isn't always true)
            time_range_key = sorted(time_ranges.keys(), key=lambda x: len(x))[-1]
            _start, _end = time_ranges[time_range_key]
            result_count = rh.REDIS.zcount(result_key, _start, _end)
            if result_count > 0:
                ten_hash_ids = rh.REDIS.zrangebyscore(result_key, _start, _end, start=0, num=10)
                hash_id = random.choice(ten_hash_ids)
                item = self.get(hash_id, **get_kwargs)

            if result_key_is_tmp:
                rh.REDIS.delete(result_key)
        elif self.size > 0:
            while item == {}:
                item = self.get_by_position(random.randint(0, self.size - 1), **get_kwargs)
        return item

    @classmethod
    def get_model(cls, base_key=None, init_args=None):
        """A class method to return a Collection object by it's base_key

        - base_key: the name of a base_key (i.e. "namespace:name")
        - init_args: the last init args used to create particular Collection
        """
        assert base_key or init_args, 'Must supply base_key or init_args'
        assert not base_key or not init_args, 'Cannot supply both base_key and init_args'
        obj = None
        if base_key:
            init_args = ih.decode(rh.REDIS.hget('_REDIS_HELPER_COLLECTION', base_key + '--last_args'))

        if not init_args:
            return
        elif init_args.startswith('Collection'):
            obj = eval('rh.' + init_args)
        else:
            data = rh.REDIS.get(init_args)
            obj = pickle.loads(data)
        return obj

    @classmethod
    def select_models(cls, named=False):
        """A class method to select previously created model instance(s)

        - named: if True, return a dict where selected model names are the
         keys and the Collection objects are the values
        """
        s = cls.init_stats(20)
        items = [
            {
                'name': name,
                'size': size
            }
            for name, size in s['sizes'].items()
        ]
        selected = ih.make_selections(
            items,
            prompt='Select the model(s) to be returned',
            item_format='{name} ({size} items)',
            wrap=False
        )

        models = [
            cls.get_model(selection['name'])
            for selection in selected
        ]
        if not named:
            return models
        else:
            return {
                model.var_name: model
                for model in models
            }

    @classmethod
    def select_model(cls):
        """A class method to select previously created model instance"""
        models = cls.select_models()
        if models:
            return models[0]

    @classmethod
    def report_all(cls):
        """A class method to show some info about the classes"""
        pprint(rh.REDIS.hgetall('_REDIS_HELPER_COLLECTION'))

    @property
    def last_update(self):
        """Return the last time the collection was updated"""
        return ih.decode(rh.REDIS.hget(
            '_REDIS_HELPER_COLLECTION',
            self._base_key + '--last_update'
        ))

    @property
    def last_update_admin(self):
        """Return the last time the collection was updated using admin format"""
        lu = self.last_update
        if lu:
            return dh.utc_float_to_pretty(lu)

    @property
    def last(self):
        """Return the last item in the collection"""
        return self.get_by_position(-1)

    @property
    def last_admin(self):
        """Return the last item in the collection using admin format for _ts"""
        return self.get_by_position(-1, admin_fmt=True)

    @property
    def first(self):
        """Return the first item in the collection"""
        return self.get_by_position(0)

    @property
    def first_admin(self):
        """Return the first item in the collection using admin format for _ts"""
        return self.get_by_position(0, admin_fmt=True)

    @property
    def size(self):
        """Return cardinality of self._ts_zset_key (number of items in the zset)"""
        return rh.REDIS.zcard(self._ts_zset_key)

    @property
    def name(self):
        """Return the name of the collection"""
        return self._name

    @property
    def namespace(self):
        """Return the namespace of the collection"""
        return self._namespace

    @property
    def var_name(self):
        """Return a valid Python variable name from name & namespace"""
        return self._var_name

    @property
    def info(self):
        s = StringIO()
        s.write('_init_args: {}'.format(self._init_args))
        s.write('\n\nsize: {}'.format(self.size))
        s.write('\n\nlast_update_admin: {}'.format(self.last_update_admin))
        s.write('\n\nkeyspace:\n')
        pprint(self.keyspace, s)
        s.write('\nindex_field_info:\n ')
        pprint(self.index_field_info(), s)
        s.write('\nmost fetched items:\n ')
        most_fetched = list(self.get_stats(10)['counts'].items())
        pprint(most_fetched, s)
        if most_fetched:
            s.write('\ntop:\n ')
            top = self.get(
                most_fetched[0][0],
                include_meta=True,
                admin_fmt=True,
                update_get_stats=False
            ),
            pprint(top, s)
        return s.getvalue()

    @property
    def now_pretty(self):
        return dh.utc_float_to_pretty()

    @property
    def now_utc_float_string(self):
        return dh.utc_now_float_string()

    @property
    def now_utc_float(self):
        return float(self.now_utc_float_string)

    @property
    def keyspace(self):
        """Show the Redis keyspace for self._base_key (excluding hash_ids)"""
        keys_generator = chain(
            rh.REDIS.scan_iter('{}:[^0-9]*'.format(self._base_key)),
            rh.REDIS.scan_iter('{}:[0-9]*_changes'.format(self._base_key)),
        )

        return sorted([
            (ih.decode(key), ih.decode(rh.REDIS.type(key)))
            for key in keys_generator
        ])

    def clear_keyspace(self):
        """Delete all Redis keys under self._base_key"""
        for key in rh.REDIS.scan_iter('{}*'.format(self._base_key)):
            rh.REDIS.delete(key)

    def delete(self, hash_id, pipe=None):
        """Delete a specific hash_id's data and remove from indexes it is in

        - hash_id: hash_id to remove
        - pipe: if a redis pipeline object is passed in, just add more
          operations to the pipe
        """
        assert hash_id.startswith(self._base_key), (
            '{} does not start with {}'.format(repr(hash_id), repr(self._base_key))
        )
        key = self._ts_zset_key
        other_key = self._in_zset_key
        score = rh.REDIS.zscore(key, hash_id)
        score2 = rh.REDIS.zscore(other_key, hash_id)
        unique_val = None
        if self._unique_field:
            number = int(hash_id.split(':')[-1])
            unique_vals = rh.REDIS.zrangebyscore(self._id_zset_key, number, number)
            if unique_vals:
                unique_val = unique_vals[0]
        if not score and not score2 and not unique_val:
            return

        if pipe is not None:
            if len(pipe.command_stack) > 1000:
                pipe.execute()
                pipe = rh.REDIS.pipeline()
            execute = False
        else:
            self.wait_for_unlock()
            self._lock()
            pipe = rh.REDIS.pipeline()
            execute = True

        pipe.delete(hash_id)
        pipe.delete(self._make_key(hash_id, '_changes'))
        pipe.hdel(
            self._get_id_stats_hash_key,
            hash_id + '--count',
            hash_id + '--last_access',
        )
        if score:
            pipe.zrem(key, hash_id)
        if score2:
            pipe.zrem(other_key, hash_id)
        if unique_val:
            pipe.zrem(self._id_zset_key, unique_val)

        index_fields = ','.join(self._index_base_keys.keys())
        if index_fields:
            for k, v in self.get(hash_id, index_fields).items():
                old_index_key = self._make_key(self._base_key, k, v)
                pipe.srem(old_index_key, hash_id)
                pipe.zincrby(self._index_base_keys[k], v, -1)

        pipe.hset('_REDIS_HELPER_COLLECTION', self._base_key + '--last_update', self.now_utc_float)

        if execute:
            val = pipe.execute()
            rh.REDIS.hset('_REDIS_HELPER_COLLECTION', self._base_key + '--last_size', self.size)
            self._unlock()
            return val

    def delete_many(self, *hash_ids):
        """Wrapper to self.delete"""
        self.wait_for_unlock()
        self._lock()
        pipe = rh.REDIS.pipeline()
        for hash_id in hash_ids:
            self.delete(hash_id, pipe)
        val = pipe.execute()
        rh.REDIS.hset('_REDIS_HELPER_COLLECTION', self._base_key + '--last_size', self.size)
        self._unlock()
        if val:
            return val[-1]

    def delete_where(self, terms='', limit=None, desc=False, insert_ts=False):
        """Wrapper to self.delete_many

        - terms: string of 'index_field:value' pairs
        - limit: max number of items to delete (None to delete all matching)
        - desc: if False and limit is not None, delete the oldest limit matches,
          if True and limit is not None, delete the newest limit matches
        - insert_ts: if True, use score of insert time instead of modify time
        """
        assert terms or limit, 'Must specify terms or a limit'
        ids = self.find(
            terms=terms,
            limit=limit,
            desc=desc,
            insert_ts=insert_ts,
            item_format='{_id}'
        )
        if ids:
            return self.delete_many(*ids)

    def delete_to(self, score=None, ts='', tz=None, insert_ts=False):
        """Delete all items with a score (timestamp) between 0 and score

        - score: a utc_float
        - ts: a timestamp with form between YYYY and YYYY-MM-DD HH:MM:SS.f
          (in the timezone specified in tz or dh.ADMIN_TIMEZONE)
        - tz: a timezone
        - insert_ts: if True, use score of insert time instead of modify time
        """
        if ts:
            tz = tz or dh.ADMIN_TIMEZONE
            score = float(dh.date_string_to_utc_float_string(ts, tz))
        if score is None:
            return
        key = self._ts_zset_key if not insert_ts else self._in_zset_key
        ids = [
            ih.decode(hash_id)
            for hash_id in rh.REDIS.zrangebyscore(key, 0, score)
        ]
        if ids:
            return self.delete_many(*ids)

    def update(self, hash_id, **data):
        """Update data at a particular hash_id

        If a unique_field is being used, it cannot be updated
        """
        assert hash_id.startswith(self._base_key), (
            '{} does not start with {}'.format(repr(hash_id), repr(self._base_key))
        )
        for mf in META_FIELDS:
            assert mf not in data, (
                '{} is a meta field that cannot be saved or updated'.format(repr(mf))
            )
        if self._unique_field:
            assert self._unique_field not in data, (
                '{} is the unique field and cannot be updated'.format(repr(self._unique_field))
            )
        score = rh.REDIS.zscore(self._ts_zset_key, hash_id)
        if score is None or data == {}:
            return
        errors = self.validate(**data)
        if errors:
            raise Exception('Validation errors: ' + repr(errors))

        self.wait_for_unlock()
        self._lock()
        changes = []
        now = self.now_utc_float
        update_fields = ','.join(data.keys())
        changes_hash_key = self._make_key(hash_id, '_changes')
        old_timestamp = rh.REDIS.zscore(self._ts_zset_key, hash_id)
        pipe = rh.REDIS.pipeline()
        pipe.hset('_REDIS_HELPER_COLLECTION', self._base_key + '--last_update', self.now_utc_float)
        for field, old_value in self.get(hash_id, update_fields).items():
            if ih.from_string(data[field]) != old_value:
                changes.append('{} {}: {} | {}'.format(hash_id, field, old_value, data[field]))
                k = '{}--{}'.format(field, old_timestamp)
                pipe.hset(changes_hash_key, k, old_value)
                if field in self._index_base_keys:
                    old_index_key = self._make_key(self._base_key, field, old_value)
                    index_key = self._make_key(self._base_key, field, data[field])
                    pipe.srem(old_index_key, hash_id)
                    pipe.zincrby(self._index_base_keys[field], old_value, -1)
                    pipe.sadd(index_key, hash_id)
                    pipe.zincrby(self._index_base_keys[field], data[field], 1)
                elif field in self._json_fields:
                    data[field] = ujson.dumps(data[field])
                elif field in self._pickle_fields:
                    data[field] = pickle.dumps(data[field])
            else:
                data.pop(field)

        if data:
            pipe.hmset(hash_id, data)
            pipe.zadd(self._ts_zset_key, now, hash_id)
            pipe.execute()
        self._unlock()
        return changes

    def validate(self, **data):
        """Validate all fields in data that have a regex; Return list of errors"""
        errors = []
        for field, value in data.items():
            if field in self.field_rx_dict:
                if not self.field_rx_dict[field].match(value):
                    errors.append((field, value, self.field_rx_dict[field].pattern))
        return errors

    def reindex(self):
        """Re-index whatever data is currently in the collection

        This should only have to be done if new field names are added to
        'index_fields' (via modifying init args to define the Collection instance)

        This should also be run if changing the value of the insert_ts init arg
        """
        self.wait_for_unlock()
        self._lock()

        pipe = rh.REDIS.pipeline()
        for index_base_key in self._index_base_keys.values():
            for key in rh.REDIS.scan_iter('{}*'.format(index_base_key)):
                pipe.delete(ih.decode(key))
        pipe.execute()

        pipe = rh.REDIS.pipeline()
        base_key_counts = {}
        for hash_id in rh.zshow(self._ts_zset_key, withscores=False):
            hash_id = ih.decode(hash_id)
            data = self.get(hash_id)

            for index_field, base_key in self._index_base_keys.items():
                index_field_data = data.get(index_field)
                key_name = self._make_key(base_key, index_field_data)
                pipe.sadd(key_name, hash_id)
                try:
                    base_key_counts[base_key][index_field_data] += 1
                except KeyError:
                    try:
                        base_key_counts[base_key][index_field_data] = 1
                    except KeyError:
                        base_key_counts[base_key] = {}
                        base_key_counts[base_key][index_field_data] = 1

        for base_key, count_dict in base_key_counts.items():
            for count_name, value in count_dict.items():
                pipe.zadd(base_key, value, count_name)

        if not self._insert_ts:
            pipe.delete(self._in_zset_key)

        pipe.execute()

        if self._insert_ts:
            pipe = rh.REDIS.pipeline()
            has_insert_ts = set(rh.zshow(self._in_zset_key, withscores=False))
            for hash_id, float_string in rh.zshow(self._ts_zset_key):
                if hash_id not in has_insert_ts:
                    pipe.zadd(self._in_zset_key, float_string, ih.decode(hash_id))
            pipe.execute()

        self._unlock()

    def old_data_for_hash_id(self, hash_id):
        """Return info about fields that have been modified on the hash_id"""
        assert hash_id.startswith(self._base_key), (
            '{} does not start with {}'.format(repr(hash_id), repr(self._base_key))
        )
        results = []
        changes_hash_key = self._make_key(hash_id, '_changes')
        for name, value in rh.REDIS.hgetall(changes_hash_key).items():
            field, timestamp = ih.decode(name).split('--')
            results.append({
                '_ts_raw': timestamp,
                '_ts_admin': dh.utc_float_to_pretty(
                    timestamp, fmt=dh.ADMIN_DATE_FMT, timezone=dh.ADMIN_TIMEZONE
                ),
                'field': field,
                'value': ih.decode(value),
            })
        results.sort(key=lambda x: (x['_ts_raw'], x['field']))
        return results

    def old_data_for_unique_value(self, unique_val):
        """Wrapper to self.old_data_for_hash_id"""
        hash_id = self.get_hash_id_for_unique_value(unique_val)
        return self.old_data_for_hash_id(hash_id)

    def recent_unique_values(self, limit=10):
        """Return list of limit most recent unique values

        - limit: max number of results to return (default 10)
            - if None is passed, then all results will be returned
        """
        limit = self.size if limit is None else limit
        return [
            ih.decode(val)
            for val in rh.REDIS.zrevrange(self._id_zset_key, start=0, end=limit-1)
        ]

    def all_unique_values(self):
        """Return list of all unique values"""
        return self.recent_unique_values(limit=None)

    def top_values_for_index(self, index_name, limit=10):
        """Return a list of tuples containing top values and counts for 'index_name'

        - index_name: name of index field to get top values and counts for
            - if index_name is the self._unique_field, the order by most recent
        - limit: max number of results to return (default 10)
            - if None is passed, then all results will be returned
        """
        limit = self.size if limit is None else limit
        if index_name is self._unique_field:
            return [
                (value, 1)
                for value in self.recent_unique_values(limit=limit)
            ]

        assert index_name in self._index_base_keys, (
            '{} is not in {}'.format(repr(index_name), repr(sorted(list(self._index_base_keys.keys()))))
        )
        base_key = self._index_base_keys[index_name]
        return [
            (ih.decode(name), int(count))
            for name, count in rh.zshow(base_key, end=limit-1)
        ]

    def index_field_info(self, limit=10):
        """Return list of 2-item tuples (index_field:value, count)

        - limit: number of top index values per index type (default 10)
            - if None is passed, then all results will be returned
        """
        limit = self.size if limit is None else limit
        results = []
        for index_field, base_key in sorted(self._index_base_keys.items()):
            results.extend([
                (':'.join([index_field, ih.decode(name)]), int(count))
                for name, count in rh.zshow(base_key, end=limit-1)
            ])
        return results

    def _redis_zset_from_terms(self, terms='', insert_ts=False):
        """Return Redis key containing sorted set and bool denoting if its a temp

        - terms: string of 'index_field:value' pairs separated by any of , ; |
        - insert_ts: if True, use score of insert time instead of modify time

        Also keep track of count, size, and timestamp stats for any intermediate
        temporary sets created
        """
        to_intersect = []
        tmp_keys = []
        d = defaultdict(list)
        stat_base_names = {}
        terms = ih.string_to_set(terms)
        now = self.now_utc_float
        zset_key = self._ts_zset_key if not insert_ts else self._in_zset_key
        for term in terms:
            index_field, *value = term.split(':')
            value = ':'.join(value)
            d[index_field].append(term)
        for index_field, grouped_terms in d.items():
            if len(grouped_terms) > 1:
                # Compute the union of all index_keys for the same field
                tmp_key = self._get_next_find_key()
                stat_base_names[';'.join(sorted(grouped_terms))] = tmp_key
                tmp_keys.append(tmp_key)
                rh.REDIS.sunionstore(
                    tmp_key,
                    *[
                        self._make_key(self._base_key, term)
                        for term in grouped_terms
                    ]
                )
                to_intersect.append(tmp_key)
            else:
                k = self._make_key(self._base_key, grouped_terms[0])
                stat_base_names[grouped_terms[0]] = k
                to_intersect.append(k)

        if len(to_intersect) > 1:
            intersect_key = self._get_next_find_key()
            tmp_keys.append(intersect_key)
            stat_base_names[';'.join(sorted(stat_base_names.keys()))] = intersect_key
            rh.REDIS.sinterstore(intersect_key, *to_intersect)
            last_key = self._get_next_find_key()
            tmp_keys.append(last_key)
            rh.REDIS.zinterstore(last_key, (intersect_key, zset_key), aggregate='MAX')
        elif len(to_intersect) == 1:
            last_key = self._get_next_find_key()
            tmp_keys.append(last_key)
            rh.REDIS.zinterstore(last_key, (to_intersect[0], zset_key), aggregate='MAX')
        else:
            last_key = zset_key

        if stat_base_names:
            pipe = rh.REDIS.pipeline()
            for stat_base, set_name in stat_base_names.items():
                set_len = rh.REDIS.scard(set_name)
                if set_len == 0:
                    pipe.zrem(self._find_searches_zset_key, stat_base)
                    pipe.hdel(
                        self._find_stats_hash_key,
                        stat_base + '--count',
                        stat_base + '--last_size',
                    )
                else:
                    pipe.zadd(self._find_searches_zset_key, now, stat_base)
                    pipe.hincrby(self._find_stats_hash_key, stat_base + '--count', 1)
                    pipe.hset(
                        self._find_stats_hash_key,
                        stat_base + '--last_size',
                        set_len
                    )
            pipe.execute()

        if tmp_keys:
            for tmp_key in tmp_keys[:-1]:
                rh.REDIS.delete(tmp_key)
            tmp_keys = [tmp_keys[-1]]

        return (last_key, tmp_keys != [])

    def find(self, terms='', start=None, end=None, limit=20, desc=None,
             get_fields='', all_fields=False, count=False, ts_fmt=None,
             ts_tz=None, admin_fmt=False, start_ts='', end_ts='', since='',
             until='', include_meta=True, item_format='', insert_ts=False,
             load_ref_data=False, post_fetch_sort_key='', sort_key_default_val=''):
        """Return a list of dicts (or dict of list of dicts) that match all terms

        Multiple values in (terms, get_fields, start_ts, end_ts, since, until)
        must be separated by any of , ; |

        - terms: string of 'index_field:value' pairs
        - start: utc_float
        - end: utc_float
        - limit: max number of results to return (default 20)
            - if None is passed, then all results will be returned
        - desc: if True, return results in descending order; if None,
          auto-determine if desc should be True or False
        - get_fields: string of field names to get for each matching hash_id
        - all_fields: if True, return all fields of each matching hash_id
        - count: if True, only return the total number of results (per time range)
        - ts_fmt: strftime format for the returned timestamps (_ts field)
        - ts_tz: a timezone to convert the timestamp to before formatting
        - admin_fmt: if True, use format and timezone defined in settings file
        - start_ts: timestamps with form between YYYY and YYYY-MM-DD HH:MM:SS.f
          (in the timezone specified in ts_tz or dh.ADMIN_TIMEZONE)
        - end_ts: timestamps with form between YYYY and YYYY-MM-DD HH:MM:SS.f
          (in the timezone specified in ts_tz or dh.ADMIN_TIMEZONE)
        - since: 'num:unit' strings (i.e. 15:seconds, 1.5:weeks, etc)
        - until: 'num:unit' strings (i.e. 15:seconds, 1.5:weeks, etc)
        - include_meta: if True (and 'count' is False), include attributes
          _id, _ts, and _pos in the results
        - item_format: format string for each item
        - insert_ts: if True, use score of insert time instead of modify time
        - load_ref_data: if True, update every result with info from any
          collections specified in reference_fields that also appears in get_fields
        - post_fetch_sort_key: key of data to sort results by right before returning
            - no effect if 'item_format' is specified
        - sort_key_default_val: default value to use when sort key does not exist
        """
        limit = self.size if limit is None else limit
        if item_format:
            # Ensure that all fields specified in item_format are fetched
            fields_in_string = set(_CURLY_MATCHER(item_format).get('curly_group_list', []))
            get_fields = ','.join(fields_in_string - META_FIELDS)
            if META_FIELDS.intersection(fields_in_string):
                include_meta = True
        elif post_fetch_sort_key:
            # Ensure that the post_fetch_sort_key is fetched
            if post_fetch_sort_key in META_FIELDS:
                include_meta = True
            elif not all_fields and post_fetch_sort_key not in get_fields:
                get_fields += ',{}'.format(post_fetch_sort_key)

        results = {}
        now = self.now_utc_float_string
        result_key, result_key_is_tmp = self._redis_zset_from_terms(terms, insert_ts)
        time_ranges = dh.get_time_ranges_and_args(
            tz=ts_tz,
            now=now,
            start=start,
            end=end,
            start_ts=start_ts,
            end_ts=end_ts,
            since=since,
            until=until
        )
        timestamp_formatter = dh.get_timestamp_formatter_from_args(
            ts_fmt=ts_fmt,
            ts_tz=ts_tz,
            admin_fmt=admin_fmt
        )

        for name, start_end_tuple in time_ranges.items():
            _start, _end = start_end_tuple
            if count:
                if _start > 0 or _end < float('inf'):
                    func = partial(rh.REDIS.zcount, result_key, _start, _end)
                else:
                    func = partial(rh.REDIS.zcard, result_key)
                results[name] = func()
            else:
                _desc = desc
                if _desc is None:
                    if 'start' in name or 'since' in name:
                        _desc = False
                    else:
                        _desc = True

                if _desc:
                    func = partial(
                        rh.REDIS.zrevrangebyscore, result_key, _end, _start,
                        start=0, num=limit, withscores=True
                    )
                else:
                    func = partial(
                        rh.REDIS.zrangebyscore, result_key, _start, _end,
                        start=0, num=limit, withscores=True
                    )

                i = 0
                _results = []
                for hash_id, timestamp in func():
                    if all_fields:
                        d = self.get(
                            hash_id,
                            include_meta=include_meta,
                            timestamp_formatter=timestamp_formatter,
                            item_format=item_format,
                            load_ref_data=load_ref_data,
                        )
                        if include_meta and not item_format:
                            d['_pos'] = i
                    elif get_fields:
                        d = self.get(
                            hash_id,
                            get_fields,
                            include_meta=include_meta,
                            timestamp_formatter=timestamp_formatter,
                            item_format=item_format,
                            load_ref_data=load_ref_data,
                        )
                        if include_meta and not item_format:
                            d['_pos'] = i
                    else:
                        d = {}
                        if include_meta:
                            d['_id'] = ih.decode(hash_id)
                            d['_ts'] = timestamp_formatter(timestamp)
                            d['_pos'] = i
                        if item_format:
                            d = item_format.format(**d)
                    _results.append(d)
                    i += 1
                results[name] = _results

        if result_key_is_tmp:
            rh.REDIS.delete(result_key)

        def _key_func(x):
            val = x.get(post_fetch_sort_key, sort_key_default_val)
            if val is None:
                val = sort_key_default_val
            return val

        if len(results) == 1:
            results = list(results.values())[0]
            if not item_format and post_fetch_sort_key:
                results.sort(
                    key=_key_func,
                    reverse=desc is True
                )
        elif len(results) > 1 and not item_format and post_fetch_sort_key:
            for section in results:
                results[section].sort(
                    key=_key_func,
                    reverse=desc is True
                )
        return results

    def select_and_modify(self, menu_item_format='', action='update',
                          prompt='', update_fields='', **find_kwargs):
        """Find items matching 'find_kwargs', make selections, then perform action

        - menu_item_format: format string for each menu item
        - action: 'update' or 'delete'
        - update_fields: (required if action is update)... a string containing
          fields to update, separated by any of , ; |
        - find_kwargs: a dict of kwargs for the self.find method
            - note: admin_fmt=True and include_meta=True cannot be over-written

        If the action was 'update', return a list of hash_ids that were modified.
        If the action was 'delete', return a list redis pipe execution results
        per selected item (list of lists)
        """
        assert action in ('update', 'delete'), 'action can only be "update" or "delete"'
        update_fields = ih.string_to_set(update_fields)
        if action == 'update':
            assert update_fields != set(), 'update_fields is required if action is "update"'
            assert self._unique_field not in update_fields, (
                '{} is the unique field and cannot be updated'.format(repr(self._unique_field))
            )
        find_kwargs.update(dict(admin_fmt=True, include_meta=True))
        if 'item_format' in find_kwargs:
            menu_item_format = find_kwargs.pop('item_format')
            find_kwargs['all_fields'] = False
            find_kwargs['get_fields'] = ','.join(ih.get_keys_in_string(menu_item_format))
        elif menu_item_format:
            find_kwargs['all_fields'] = False
            find_kwargs['get_fields'] = ','.join(ih.get_keys_in_string(menu_item_format))

        found = self.find(**find_kwargs)
        assert type(found) == list, 'Results contain multiple time ranges... not allowed for now'
        selected = ih.make_selections(
            found,
            prompt=prompt,
            item_format=menu_item_format,
            wrap=False
        )

        if selected:
            print('\nSelected:')
            if menu_item_format:
                print('\n'.join([menu_item_format.format(**x) for x in selected]) + '\n')
            else:
                print('\n'.join([repr(x) for x in selected]) + '\n')
            results = []
            if action == 'update':
                new_data = {}
                for field in update_fields:
                    resp = ih.user_input('value for {} field'.format(repr(field)))
                    if resp:
                        new_data[field] = resp
                if new_data:
                    for item in selected:
                        results.append(self.update(item['_id'], **new_data))
            elif action == 'delete':
                for item in selected:
                    results.append(self.delete(item['_id']))

            return results

    def find_stats(self, limit=5):
        """Return summary info for temporary sets created during 'find' calls

        - limit: max number of items to return in 'counts' and 'sizes' info
        """
        count_stats = []
        size_stats = []
        results = {}
        for name, num in rh.REDIS.hgetall(self._find_stats_hash_key).items():
            name, _type = ih.decode(name).rsplit('--', 1)
            if _type == 'count':
                count_stats.append((name, int(ih.decode(num))))
            elif _type == 'last_size':
                size_stats.append((name, int(ih.decode(num))))
        count_stats.sort(key=lambda x: x[1], reverse=True)
        size_stats.sort(key=lambda x: x[1], reverse=True)
        results['counts'] = OrderedDict(count_stats[:limit])
        results['sizes'] = OrderedDict(size_stats[:limit])
        results['timestamps'] = OrderedDict()
        newest = rh.zshow(self._find_searches_zset_key, end=3*(limit-1))
        for name, ts in newest:
            results['timestamps'][ih.decode(name)] = (
                ts,
                dh.utc_float_to_pretty(ts, fmt=dh.ADMIN_DATE_FMT, timezone=dh.ADMIN_TIMEZONE)
            )
        return results

    @classmethod
    def init_stats(cls, limit=5):
        """Return summary info about last size and update time of Collection items

        - limit: max number of ids to return
        """
        size_stats = []
        update_stats = []
        results = {'init_args': {}}
        for key, val in rh.REDIS.hgetall('_REDIS_HELPER_COLLECTION').items():
            base_key, _type = ih.decode(key).rsplit('--', 1)
            if _type == 'last_size':
                size_stats.append((base_key, int(ih.decode(val))))
            elif _type == 'last_update':
                update_stats.append((
                    base_key,
                    (
                        ih.decode(val),
                        dh.utc_float_to_pretty(ih.decode(val), fmt=dh.ADMIN_DATE_FMT, timezone=dh.ADMIN_TIMEZONE)
                    )
                ))
            elif _type == 'last_args':
                results['init_args'][base_key] = ih.decode(val)
        size_stats.sort(key=lambda x: x[1], reverse=True)
        update_stats.sort(key=lambda x: x[1], reverse=True)
        results['sizes'] = OrderedDict(size_stats[:limit])
        results['timestamps'] = OrderedDict(update_stats[:limit])
        return results

    def get_stats(self, limit=5):
        """Return summary info about ids and fields accessed by self.get

        - limit: max number of ids to return
        """
        count_stats = []
        access_stats = []
        results = {}
        for name, num in rh.REDIS.hgetall(self._get_id_stats_hash_key).items():
            name, _type = ih.decode(name).rsplit('--', 1)
            if _type == 'count':
                count_stats.append((name, int(ih.decode(num))))
            elif _type == 'last_access':
                access_stats.append((
                    name,
                    (
                        ih.decode(num),
                        dh.utc_float_to_pretty(ih.decode(num), fmt=dh.ADMIN_DATE_FMT, timezone=dh.ADMIN_TIMEZONE)
                    )
                ))
        count_stats.sort(key=lambda x: x[1], reverse=True)
        access_stats.sort(key=lambda x: x[1], reverse=True)
        results['counts'] = OrderedDict(count_stats[:limit])
        results['timestamps'] = OrderedDict(access_stats[:limit])
        field_stats = [
            (ih.decode(name), int(ih.decode(count)))
            for name, count in rh.REDIS.hgetall(self._get_field_stats_hash_key).items()
        ]
        field_stats.sort(key=lambda x: x[1], reverse=True)
        results['fields'] = OrderedDict(field_stats)
        return results

    def clear_find_stats(self):
        """Delete all Redis keys under self._find_base_key"""
        pipe = rh.REDIS.pipeline()
        for key in rh.REDIS.scan_iter('{}*'.format(self._find_base_key)):
            pipe.delete(key)
        pipe.execute()

    def clear_init_stats(self):
        """Delete stats stored in self.__class__.__name__ or _REDIS_HELPER_COLLECTION keys"""
        pipe = rh.REDIS.pipeline()
        pipe.delete(self.__class__.__name__)
        pipe.delete('_REDIS_HELPER_COLLECTION')
        pipe.execute()

    def clear_get_stats(self):
        """Delete stats stored in self._get_id_stats_hash_key & self._get_field_stats_hash_key"""
        pipe = rh.REDIS.pipeline()
        pipe.delete(self._get_id_stats_hash_key)
        pipe.delete(self._get_field_stats_hash_key)
        pipe.execute()
