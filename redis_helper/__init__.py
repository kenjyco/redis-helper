import configparser
import os.path
import textwrap
import pytz
import logging
import input_helper as ih
from os import getenv, makedirs
from shutil import copyfile
from datetime import datetime, timedelta, timezone as dt_timezone
from functools import partial
from itertools import product, zip_longest, chain
from redis import StrictRedis


__doc__ = """Create an instance of `redis_helper.Collection` and use it

import redis_helper as rh
model = rh.Collection(...)
"""


LOGFILE = os.path.abspath('log--redis-helper.log')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(LOGFILE, mode='a')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(funcName)s: %(message)s'
))
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
logger.addHandler(file_handler)
logger.addHandler(console_handler)


def _get_settings_file():
    home_config_dir = os.path.expanduser('~/.config/redis-helper')
    this_dir = os.path.abspath(os.path.dirname(__file__))
    settings_file = os.path.join(home_config_dir, 'settings.ini')
    if not os.path.isfile(settings_file):
        default_settings = os.path.join(this_dir, 'settings.ini')
        try:
            makedirs(home_config_dir)
        except FileExistsError:
            pass
        print('copying {} -> {}'.format(repr(default_settings), repr(settings_file)))
        copyfile(default_settings, settings_file)

    return settings_file


SETTINGS_FILE = _get_settings_file()
APP_ENV = getenv('APP_ENV', 'dev')
FLOAT_STRING_FMT = '%Y%m%d%H%M%S.%f'
_config = configparser.RawConfigParser()
_config.read(SETTINGS_FILE)


def get_setting(name, default='', section=APP_ENV):
    """Get a setting from settings.ini for a particular section

    If item is not found in the section, look for it in the 'default' section.
    If item is not found in the default section of settings.ini, return the
    default value
    """
    try:
        val = _config[section][name]
    except KeyError:
        try:
            val = _config['default'][name]
        except KeyError:
            return default
        else:
            val = ih.from_string(val)
    else:
        val = ih.from_string(val)
    return val


def dt_to_float_string(dt, fmt=FLOAT_STRING_FMT):
    """Return string representation of a utc_float from given dt object"""
    return dt.strftime(fmt)


def float_string_to_dt(float_string, fmt=FLOAT_STRING_FMT):
    """Return a dt object from a utc_float"""
    return datetime.strptime(str(float_string), fmt)


def utc_now_float_string(fmt=FLOAT_STRING_FMT):
    """Return string representation of a utc_float for right now"""
    return dt_to_float_string(datetime.utcnow(), fmt)


def utc_ago_float_string(num_unit, now=None, fmt=FLOAT_STRING_FMT):
    """Return a float_string representing a UTC datetime in the past

    - num_unit: a string 'num:unit' (i.e. 15:seconds, 1.5:weeks, etc)
    - now: a utc_float or None

    Valid units are: (se)conds, (mi)nutes, (ho)urs, (da)ys, (we)eks, hr, wk
    """
    if now is None:
        now = datetime.utcnow()
    else:
        now = float_string_to_dt(now)
    val = None
    num, unit = num_unit.split(':')
    _trans = {
        'se': 'seconds', 'mi': 'minutes', 'ho': 'hours', 'hr': 'hours',
        'da': 'days', 'we': 'weeks', 'wk': 'weeks'
    }
    try:
        kwargs = {_trans[unit.lower()[:2]]: float(num)}
    except (KeyError, ValueError) as e:
        pass
    else:
        td = timedelta(**kwargs)
        val = dt_to_float_string(now - td, fmt)
    return val


def utc_float_to_pretty(utc_float=None, fmt=None, timezone=None):
    """Return the formatted version of utc_float

    - fmt: a strftime format
    - timezone: a timezone

    If no utc_float is provided, a utc_float for "right now" will be used. If no
    fmt is provided and admin_date_fmt is in settings.ini, settings will be used
    """
    if not utc_float:
        utc_float = float(utc_now_float_string())
    if not fmt:
        if ADMIN_DATE_FMT:
            fmt = ADMIN_DATE_FMT
            timezone = ADMIN_TIMEZONE
        else:
            return utc_float
    dt = datetime.strptime(str(utc_float), FLOAT_STRING_FMT)
    if timezone:
        dt = dt.replace(tzinfo=dt_timezone.utc)
        dt = dt.astimezone(pytz.timezone(timezone))
    return dt.strftime(fmt)


def date_string_to_utc_float_string(date_string, timezone=None):
    """Return a utc_float_string for a given date_string

    - date_string: string form between 'YYYY' and 'YYYY-MM-DD HH:MM:SS.f'
    """
    dt = None
    s = None
    for fmt in [
        '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d %H', '%Y-%m-%d', '%Y-%m', '%Y'
    ]:
        try:
            dt = datetime.strptime(str(date_string), fmt)
        except ValueError:
            continue
        else:
            break

    if dt:
        if timezone:
            tz = pytz.timezone(timezone)
            dt = tz.localize(dt).astimezone(pytz.utc)
        s = dt_to_float_string(dt)
    return s


def get_time_ranges_and_args(**kwargs):
    """Return a dict of time range strings and start/end tuples

    Multiple values in (start_ts, end_ts, since, until) must be separated
    by any of , ; |

    - tz: timezone
    - now: float_string
    - start: utc_float
    - end: utc_float
    - start_ts: timestamps with form between YYYY and YYYY-MM-DD HH:MM:SS.f (in tz)
    - end_ts: timestamps with form between YYYY and YYYY-MM-DD HH:MM:SS.f (in tz)
    - since: 'num:unit' strings (i.e. 15:seconds, 1.5:weeks, etc)
    - until: 'num:unit' strings (i.e. 15:seconds, 1.5:weeks, etc)

    The start/end kwargs returned are meant to be used with any of
    REDIS functions zcount, zrangebyscore, or zrevrangebyscore
    """
    tz = kwargs.get('tz') or ADMIN_TIMEZONE
    now = kwargs.get('now') or utc_now_float_string()
    results = {}
    _valid_args = [
        ('start_ts', 'end_ts', partial(date_string_to_utc_float_string, timezone=tz)),
        ('since', 'until', partial(utc_ago_float_string, now=now)),
    ]
    for first, second, func in _valid_args:
        first_string = kwargs.get(first, '')
        second_string = kwargs.get(second, '')
        if first_string or second_string:
            first_vals = ih.string_to_set(first_string)
            second_vals = ih.string_to_set(second_string)
            if first_vals and second_vals:
                _gen = product(first_vals, second_vals)
                gen = chain(
                    _gen,
                    ((f, '') for f in first_vals),
                    (('', s) for s in second_vals)
                )
            else:
                gen = zip_longest(first_vals, second_vals)

            for _first, _second in gen:
                if _first and _second:
                    return_key = '{}={},{}={}'.format(first, _first, second, _second)
                    start_float = float(func(_first))
                    end_float = float(func(_second))
                elif _first:
                    return_key = '{}={}'.format(first, _first)
                    start_float = float(func(_first))
                    end_float = float('inf')
                elif _second:
                    return_key = '{}={}'.format(second, _second)
                    end_float = float(func(_second))
                    start_float = 0
                else:
                    continue
                if start_float >= end_float:
                    continue

                results[return_key] = (start_float, end_float)

    start = kwargs.get('start')
    end = kwargs.get('end')
    if start and end:
        return_key = 'start={},end={}'.format(start, end)
        results[return_key] = (float(start), float(end))
    elif start:
        return_key = 'start={}'.format(start)
        results[return_key] = (float(start), float('inf'))
    elif end:
        return_key = 'end={}'.format(end)
        results[return_key] = (0, float(end))
    if not results:
        results['all'] = (0, float('inf'))
    return results


def get_timestamp_formatter_from_args(ts_fmt=None, ts_tz=None, admin_fmt=False):
    """Return a function that can be applied to a utc_float

    - ts_fmt: strftime format for the returned timestamp
    - ts_tz: a timezone to convert the timestamp to before formatting
    - admin_fmt: if True, use format and timezone defined in settings file
    """
    if admin_fmt:
        func = partial(
            utc_float_to_pretty, fmt=ADMIN_DATE_FMT, timezone=ADMIN_TIMEZONE
        )
    elif ts_tz and ts_fmt:
        func = partial(utc_float_to_pretty, fmt=ts_fmt, timezone=ts_tz)
    elif ts_fmt:
        func = partial(utc_float_to_pretty, fmt=ts_fmt)
    else:
        func = lambda x: x
    return func


def zshow(key, start=0, end=-1, desc=True, withscores=True):
    """Wrapper to REDIS.zrange"""
    return REDIS.zrange(key, start, end, withscores=withscores, desc=desc)


def identity(x):
    """Return x, unmodified"""
    return x


ADMIN_TIMEZONE = get_setting('admin_timezone')
ADMIN_DATE_FMT = get_setting('admin_date_fmt')
REDIS_URL = get_setting('redis_url')
REDIS = StrictRedis.from_url(REDIS_URL) if REDIS_URL is not '' else None
from .collection import Collection
