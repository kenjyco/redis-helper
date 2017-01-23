import re
import configparser
import os.path
import textwrap
import pytz
from os import getenv
from shutil import copyfile
from datetime import datetime, timedelta, timezone as dt_timezone
from functools import partial
from itertools import product, zip_longest, chain
from redis import StrictRedis


__doc__ = """Easily store, index, and modify Python dicts in Redis (with flexible searching)

Use `RedThing` to get a client for each of your models.
"""


def _get_settings_file():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(root_dir)
    home_config_dir = os.path.expanduser('~/.config/redis-helper')
    for dirname in (project_dir, home_config_dir, '/etc/redis-helper'):
        settings_file = os.path.join(dirname, 'settings.ini')
        if os.path.isfile(settings_file):
            return settings_file

    # Copy the sample settings file in project_dir and return it
    sample_file = os.path.join(project_dir, 'settings.ini.sample')
    settings_file = os.path.join(home_config_dir, 'settings.ini')
    if not os.path.exists(home_config_dir):
        os.makedirs(home_config_dir)
    copyfile(sample_file, settings_file)
    print('\nCopied settings to {}'.format(repr(settings_file)))
    return settings_file


SETTINGS_FILE = _get_settings_file()
APP_ENV = getenv('APP_ENV', 'dev')
FLOAT_STRING_FMT = '%Y%m%d%H%M%S.%f'
_config = configparser.RawConfigParser()
_config.read(SETTINGS_FILE)


def from_string(val):
    """Return simple bool, int, and float values contained in a string

    Useful for converting items in settings.ini or values pulled from Redis
    """
    if val.lower() == 'true':
        val = True
    elif val.lower() == 'false':
        val = False
    else:
        try:
            val = float(val)
            if val.is_integer():
                val = int(val)
        except ValueError:
            try:
                val = int(val)
            except ValueError:
                pass
    return val


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
            val = from_string(val)
    else:
        val = from_string(val)
    return val


def string_to_set(s):
    """Return a set of strings from s where items are separated by any of , ; |"""
    return set(re.split(r'\s*[,;\|]\s*', s)) - set([''])


def dt_to_float_string(dt, fmt=FLOAT_STRING_FMT):
    """Return string representation of a utc_float from given dt object"""
    return dt.strftime(fmt)


def float_string_to_dt(float_string, fmt=FLOAT_STRING_FMT):
    """Return a dt object from a utc_float"""
    return datetime.strptime(float_string, fmt)


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
            dt = datetime.strptime(date_string, fmt)
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
            first_vals = string_to_set(first_string)
            second_vals = string_to_set(second_string)
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


def decode(obj, encoding='utf-8'):
    """Decode the bytes of an object to an encoding"""
    try:
        return obj.decode(encoding)
    except (AttributeError, UnicodeDecodeError):
        return obj


def identity(x):
    """Return x, unmodified"""
    return x


def user_input(prompt_string='input', ch='> '):
    """Prompt user for input

    - prompt_string: string to display when asking for input
    - ch: string appended to the main prompt_string
    """
    try:
        return input(prompt_string + ch)
    except (EOFError, KeyboardInterrupt):
        print()
        return ''


def make_selections(items, prompt='', wrap=True, item_format=''):
    """Generate a menu from items, then return a subset of the items provided

    - items: list of strings or list of dicts
    - prompt: string to display when asking for input
    - wrap: True/False for whether or not to wrap long lines
    - item_format: format string for each item (when items are dicts)

    Note: selection order is preserved in the returned items
    """
    if not items:
        return items

    selected = []

    if not prompt:
        prompt = 'Make selections (separate by space): '

    make_string = identity
    if item_format:
        make_string = lambda x: item_format.format(**x)

    # Generate the menu and display the items user will select from
    for i, item in enumerate(items):
        if i % 5 == 0 and i > 0:
            print('-' * 70)
        try:
            line = '{:4}) {}'.format(i, make_string(item))
        except UnicodeEncodeError:
            item = {
                k: v.encode('ascii', 'replace')
                for k, v in item.items()
            }
            line = '{:4}) {}'.format(i, make_string(item))
        if wrap:
            print(textwrap.fill(line, subsequent_indent=' '*6))
        else:
            print(line)

    print()
    indices = user_input(prompt)
    if not indices:
        return []

    for index in indices.split():
        try:
            selected.append(items[int(index)])
        except (IndexError, ValueError):
            pass

    return selected


ADMIN_TIMEZONE = get_setting('admin_timezone')
ADMIN_DATE_FMT = get_setting('admin_date_fmt')
REDIS_URL = get_setting('redis_url')
REDIS = StrictRedis.from_url(REDIS_URL) if REDIS_URL is not '' else None
from .redthing import RedThing
