import pickle
import ujson
import random
import redis_helper as rh
import input_helper as ih
from collections import defaultdict
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
                 json_fields='', pickle_fields='', insert_ts=False):
        """Pass in namespace and name

        - unique_field: name of the optional unique field
        - index_fields: string of fields that should be indexed
        - json_fields: string of fields that should be serialized as JSON
        - pickle_fields: string of fields with complex/arbitrary structure
        - insert_ts: if True, use an additional index for insert times

        Separate fields in strings by any of , ; |
        """
        self._unique_field = unique_field
        index_fields_set = ih.string_to_set(index_fields)
        self._json_fields = ih.string_to_set(json_fields)
        self._pickle_fields = ih.string_to_set(pickle_fields)
        self._insert_ts = insert_ts

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

        self._base_key = self._make_key(namespace, name)
        self._index_base_keys = {
            index_field: self._make_key(self._base_key, index_field)
            for index_field in index_fields_set
        }
        self._next_id_string_key = self._make_key(self._base_key, '_next_id')
        self._ts_zset_key = self._make_key(self._base_key, '_ts')
        self._id_zset_key = self._make_key(self._base_key, '_id')
        self._in_zset_key = self._make_key(self._base_key, '_in')
        self._find_base_key = self._make_key(self._base_key, '_find')
        self._find_next_id_string_key = self._make_key(self._find_base_key, '_next_id')
        self._find_stats_hash_key = self._make_key(self._find_base_key, '_stats')
        self._find_searches_zset_key = self._make_key(self._find_base_key, '_searches')

        _parts = [
            '({}, {}'.format(repr(namespace), repr(name)),
            'unique_field={}'.format(repr(unique_field)) if unique_field else '',
            'index_fields={}'.format(repr(index_fields)) if index_fields else '',
            'json_fields={}'.format(repr(json_fields)) if json_fields else '',
            'pickle_fields={}'.format(repr(pickle_fields)) if pickle_fields else '',
            'insert_ts={}'.format(repr(insert_ts)) if insert_ts else '',
        ]
        self._init_args = ''.join([
            self.__class__.__name__,
            ', '.join([p for p in _parts if p is not '']),
            ')'
        ])
        rh.REDIS.hincrby(self.__class__.__name__, self._init_args, 1)

        if self.__class__.__name__ != 'Collection':
            item = rh.REDIS.get(self._init_args)
            if not item:
                rh.REDIS.set(self._init_args, pickle.dumps(self))

    def __repr__(self):
        return self._init_args

    def __len__(self):
        return self.size

    def __getitem__(self, i):
        if type(i) == int:
            return self.get_by_position(i, include_meta=True)
        elif type(i) == str and i.startswith(self._base_key):
            return self.get(i, include_meta=True)
        elif type(i) == str and self._unique_field and i:
            val = self.get_by_unique_value(i, include_meta=True)
            if not val:
                return self.random(i, include_meta=True)
            return val
        elif type(i) == str and i:
            return self.random(i, include_meta=True)
        elif type(i) == slice:
            return self.get_by_slice(i.start, i.stop, include_meta=True)
        else:
            return {}

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

    def add(self, **data):
        """Add all fields and values in data to the collection

        If self._unique_field is a non-empty string, that field must be provided
        in the data and there must not be an item in the collection with the
        same value for that field
        """
        if self._unique_field:
            unique_val = data.get(self._unique_field)
            assert unique_val is not None, (
                'unique field {} is not in data'.format(repr(self._unique_field))
            )
            score = rh.REDIS.zscore(self._id_zset_key, unique_val)
            assert score is None, (
                '{}={} already exists'.format(self._unique_field, repr(unique_val))
            )

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
        return key

    def get(self, hash_id, fields='', include_meta=False,
            timestamp_formatter=rh.identity, ts_fmt=None, ts_tz=None,
            admin_fmt=False, item_format='', insert_ts=False):
        """Wrapper to rh.REDIS.hget/hmget/hgetall

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
        """
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
                timestamp_formatter = rh.get_timestamp_formatter_from_args(
                    ts_fmt=ts_fmt,
                    ts_tz=ts_tz,
                    admin_fmt=admin_fmt
                )
        try:
            if num_fields == 1:
                field = fields.pop()
                data = {field: rh.REDIS.hget(hash_id, field)}
            elif num_fields > 1:
                data = dict(zip(fields, rh.REDIS.hmget(hash_id, *fields)))
            else:
                _data = rh.REDIS.hgetall(hash_id)
                data = {
                    ih.decode(k): v
                    for k, v in _data.items()
                }
        except ResponseError:
            data = {}

        for field in data.keys():
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
            key = self._ts_zset_key if not insert_ts else self._in_zset_key
            data['_id'] = ih.decode(hash_id)
            data['_ts'] = timestamp_formatter(
                rh.REDIS.zscore(key, hash_id)
            )
        if item_format:
            return item_format.format(**data)
        return data

    def get_hash_id_for_unique_value(self, unique_val):
        """Return the hash_id of the object that has unique_val in _unique_field"""
        if self._unique_field:
            score = rh.REDIS.zscore(self._id_zset_key, unique_val)
            if score:
                return self._make_key(self._base_key, int(score))

    def get_by_unique_value(self, unique_val, fields='', include_meta=False,
                            timestamp_formatter=rh.identity, ts_fmt=None,
                            ts_tz=None, admin_fmt=False, item_format=''):
        """Wrapper to self.get

        - fields: string of field names to get separated by any of , ; |
        - include_meta: if True include attributes _id and _ts
        - timestamp_formatter: a callable to apply to the _ts timestamp
        - ts_fmt: strftime format for the returned timestamps (_ts field)
        - ts_tz: a timezone to convert the timestamp to before formatting
        - admin_fmt: if True, use format and timezone defined in settings file
        - item_format: format string for each item (return a string instead of
          a dict)
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
                item_format=item_format
            )
        return data

    def get_by_position(self, pos, **kwargs):
        """Wrapper to self.get

        - insert_ts: if True, use position of insert time instead of modify time
        """
        data = {}
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
          (in the timezone specified in ts_tz or ADMIN_TIMEZONE)
        - end_ts: timestamps with form between YYYY and YYYY-MM-DD HH:MM:SS.f
          (in the timezone specified in ts_tz or ADMIN_TIMEZONE)
        - since: 'num:unit' strings (i.e. 15:seconds, 1.5:weeks, etc)
        - until: 'num:unit' strings (i.e. 15:seconds, 1.5:weeks, etc)
        - get_kwargs: dict of keyword arguments to pass to self.get
        """
        item = {}
        timestamp_formatter = rh.get_timestamp_formatter_from_args(
            ts_fmt=ts_fmt,
            ts_tz=ts_tz,
            admin_fmt=admin_fmt
        )
        get_kwargs['timestamp_formatter'] = timestamp_formatter
        if admin_fmt or ts_fmt or ts_tz:
            get_kwargs['include_meta'] = True
        if terms:
            insert_ts = get_kwargs.get('insert_ts', False)
            now = self.now_utc_float
            result_key, result_key_is_tmp = self._redis_zset_from_terms(terms, insert_ts)
            time_ranges = rh.get_time_ranges_and_args(
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
    def select_model(cls):
        """A class method to select previously created model instance"""
        items = [
            {
                'name': ih.decode(name),
                'count': ih.from_string(ih.decode(count))
            }
            for name, count in rh.REDIS.hgetall(cls.__name__).items()
        ]
        items.sort(key=lambda x: x['count'], reverse=True)
        selected = ih.make_selections(
            items,
            prompt='Select the model to be returned',
            item_format='({count} instances) {name}',
            wrap=False
        )

        if selected:
            if cls.__name__ == 'Collection':
                return eval('rh.{}'.format(selected[0]['name']))

            pickle_string = rh.REDIS.get(selected[0]['name'])
            if pickle_string:
                return pickle.loads(pickle_string)

            rh.logger.error('Unable to load model {}'.format(selected[0]['name']))

    @property
    def last(self):
        """Return the last item in the collection"""
        return self.get_by_position(-1)

    @property
    def last_admin(self):
        """Return the last item in the collection"""
        return self.get_by_position(-1, admin_fmt=True)

    @property
    def first(self):
        """Return the first item in the collection"""
        return self.get_by_position(0)

    @property
    def first_admin(self):
        """Return the first item in the collection"""
        return self.get_by_position(0, admin_fmt=True)

    @property
    def size(self):
        """Return cardinality of self._ts_zset_key (number of items in the zset)"""
        return rh.REDIS.zcard(self._ts_zset_key)

    @property
    def info(self):
        s = StringIO()
        s.write('_init_args: {}'.format(self._init_args))
        s.write('\n\nsize: {}'.format(self.size))
        s.write('\n\nkeyspace:\n')
        pprint(self.keyspace, s)
        s.write('\nindex_field_info:\n ')
        pprint(self.index_field_info(), s)
        s.write('\nrandom:\n ')
        pprint(self.random(), s)
        return s.getvalue()

    @property
    def now_pretty(self):
        return rh.utc_float_to_pretty()

    @property
    def now_utc_float(self):
        return float(rh.utc_now_float_string())

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

    def delete(self, hash_id, pipe=None, insert_ts=False):
        """Delete a specific hash_id's data and remove from indexes it is in

        - hash_id: hash_id to remove
        - pipe: if a redis pipeline object is passed in, just add more
          operations to the pipe
        - insert_ts: if True, use score of insert time instead of modify time
        """
        assert hash_id.startswith(self._base_key), (
            '{} does not start with {}'.format(repr(hash_id), repr(self._base_key))
        )
        if insert_ts:
            key = self._in_zset_key
            other_key = self._ts_zset_key
        else:
            key = self._ts_zset_key
            other_key = self._in_zset_key
        score = rh.REDIS.zscore(key, hash_id)
        if score is None:
            return
        if pipe is not None:
            execute = False
        else:
            pipe = rh.REDIS.pipeline()
            execute = True

        pipe.delete(hash_id)
        index_fields = ','.join(self._index_base_keys.keys())
        if index_fields:
            for k, v in self.get(hash_id, index_fields).items():
                old_index_key = self._make_key(self._base_key, k, v)
                pipe.srem(old_index_key, hash_id)
                pipe.zincrby(self._index_base_keys[k], v, -1)
        if self._unique_field:
            unique_val = self.get(hash_id, self._unique_field)[self._unique_field]
            pipe.zrem(key, unique_val)
            pipe.zrem(other_key, unique_val)
        pipe.delete(self._make_key(hash_id, '_changes'))
        pipe.zrem(other_key, hash_id)

        if execute:
            pipe.zrem(key, hash_id)
            return pipe.execute()

    def delete_many(self, *hash_ids, insert_ts=False):
        """Wrapper to self.delete

        - insert_ts: if True, use score of insert time instead of modify time
        """
        pipe = rh.REDIS.pipeline()
        for hash_id in hash_ids:
            self.delete(hash_id, pipe, insert_ts)
        return pipe.execute()[-1]

    def delete_to(self, score=None, ts='', tz=None, insert_ts=False):
        """Delete all items with a score (timestamp) between 0 and score

        - score: a utc_float
        - ts: a timestamp with form between YYYY and YYYY-MM-DD HH:MM:SS.f
          (in the timezone specified in tz or ADMIN_TIMEZONE)
        - tz: a timezone
        - insert_ts: if True, use score of insert time instead of modify time
        """
        if ts:
            tz = tz or rh.ADMIN_TIMEZONE
            score = float(rh.date_string_to_utc_float_string(ts, tz))
        if score is None:
            return
        key = self._ts_zset_key if not insert_ts else self._in_zset_key
        pipe = rh.REDIS.pipeline()
        for hash_id in rh.REDIS.zrangebyscore(key, 0, score):
            self.delete(hash_id, pipe, insert_ts)
        pipe.zremrangebyscore(key, 0, score)
        return pipe.execute()[-1]

    def update(self, hash_id, **data):
        """Update data at a particular hash_id

        If a unique_field is being used, it cannot be updated
        """
        assert hash_id.startswith(self._base_key), (
            '{} does not start with {}'.format(repr(hash_id), repr(self._base_key))
        )
        if self._unique_field:
            assert self._unique_field not in data, (
                '{} is the unique field and cannot be updated'.format(repr(self._unique_field))
            )
        score = rh.REDIS.zscore(self._ts_zset_key, hash_id)
        if score is None or data == {}:
            return

        now = self.now_utc_float
        update_fields = ','.join(data.keys())
        changes_hash_key = self._make_key(hash_id, '_changes')
        old_timestamp = rh.REDIS.zscore(self._ts_zset_key, hash_id)
        pipe = rh.REDIS.pipeline()
        for field, old_value in self.get(hash_id, update_fields).items():
            if data[field] != old_value:
                k = '{}--{}'.format(field, old_timestamp)
                if old_value is not None:
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
        return hash_id

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
                '_ts_admin': rh.utc_float_to_pretty(
                    timestamp, fmt=rh.ADMIN_DATE_FMT, timezone=rh.ADMIN_TIMEZONE
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
        """Return list of limit most recent unique values"""
        return [
            ih.decode(val)
            for val in rh.REDIS.zrevrange(self._id_zset_key, start=0, end=limit-1)
        ]

    def top_values_for_index(self, index_name, limit=10):
        """Return a list of tuples containing top values and counts for 'index_name'

        - index_name: name of index field to get top values and counts for
            - if index_name is the self._unique_field, the order by most recent
        """
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

        - limit: number of top index values per index type
        """
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
                pipe.zadd(self._find_searches_zset_key, now, stat_base)
                pipe.hincrby(self._find_stats_hash_key, stat_base + '--count', 1)
                pipe.hset(
                    self._find_stats_hash_key,
                    stat_base + '--last_size',
                    rh.REDIS.scard(set_name)
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
             post_fetch_sort_key='', sort_key_default_val=''):
        """Return a list of dicts (or dict of list of dicts) that match all terms

        Multiple values in (terms, get_fields, start_ts, end_ts, since, until)
        must be separated by any of , ; |

        - terms: string of 'index_field:value' pairs
        - start: utc_float
        - end: utc_float
        - limit: max number of results
        - desc: if True, return results in descending order; if None,
          auto-determine if desc should be True or False
        - get_fields: string of field names to get for each matching hash_id
        - all_fields: if True, return all fields of each matching hash_id
        - count: if True, only return the total number of results (per time range)
        - ts_fmt: strftime format for the returned timestamps (_ts field)
        - ts_tz: a timezone to convert the timestamp to before formatting
        - admin_fmt: if True, use format and timezone defined in settings file
        - start_ts: timestamps with form between YYYY and YYYY-MM-DD HH:MM:SS.f
          (in the timezone specified in ts_tz or ADMIN_TIMEZONE)
        - end_ts: timestamps with form between YYYY and YYYY-MM-DD HH:MM:SS.f
          (in the timezone specified in ts_tz or ADMIN_TIMEZONE)
        - since: 'num:unit' strings (i.e. 15:seconds, 1.5:weeks, etc)
        - until: 'num:unit' strings (i.e. 15:seconds, 1.5:weeks, etc)
        - include_meta: if True (and 'count' is False), include attributes
          _id, _ts, and _pos in the results
        - item_format: format string for each item
        - insert_ts: if True, use score of insert time instead of modify time
        - post_fetch_sort_key: key of data to sort results by right before returning
            - no effect if 'item_format' is specified
        - sort_key_default_val: default value to use when sort key does not exist
        """
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
        now = self.now_utc_float
        result_key, result_key_is_tmp = self._redis_zset_from_terms(terms, insert_ts)
        time_ranges = rh.get_time_ranges_and_args(
            tz=ts_tz,
            now=now,
            start=start,
            end=end,
            start_ts=start_ts,
            end_ts=end_ts,
            since=since,
            until=until
        )
        timestamp_formatter = rh.get_timestamp_formatter_from_args(
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
            name, _type = ih.decode(name).split('--')
            if _type == 'count':
                count_stats.append((name, int(ih.decode(num))))
            elif _type == 'last_size':
                size_stats.append((name, int(ih.decode(num))))
        count_stats.sort(key=lambda x: x[1], reverse=True)
        size_stats.sort(key=lambda x: x[1], reverse=True)
        results['counts'] = count_stats[:limit]
        results['sizes'] = size_stats[:limit]
        results['timestamps'] = []
        newest = rh.zshow(self._find_searches_zset_key, end=3*(limit-1))
        for name, ts in newest:
            results['timestamps'].append((
                ih.decode(name),
                ts,
                rh.utc_float_to_pretty(ts, fmt=rh.ADMIN_DATE_FMT, timezone=rh.ADMIN_TIMEZONE)
            ))
        return results

    def clear_find_stats(self):
        """Delete all Redis keys under self._find_base_key"""
        pipe = rh.REDIS.pipeline()
        for key in rh.REDIS.scan_iter('{}*'.format(self._find_base_key)):
            pipe.delete(key)
        pipe.execute()

    def clear_init_stats(self):
        """Delete stats stored in self.__class__.__name__ key"""
        rh.REDIS.delete(self.__class__.__name__)
