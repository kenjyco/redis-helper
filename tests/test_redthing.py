import random
import pytest
import redis_helper as rh
from redis import ConnectionError


try:
    DBSIZE = rh.REDIS.dbsize()
    REDIS_CONNECTED = True
except (ConnectionError, AttributeError):
    DBSIZE = float('inf')
    REDIS_CONNECTED = False


WORDS = ['goats', 'dogs', 'grapes', 'bananas', 'smurfs', 'snorks', 'links', 'queries']


def generate_rt1_data():
    return {
        'x': random.randint(1, 9),
        'y': random.randint(100, 999),
        'z': random.randint(10000, 99999),
    }


def generate_rt23_data():
    return {
        'a': random.choice(WORDS),
        'b': ' & '.join(random.sample(WORDS, 2)),
        'c': ', '.join(random.sample(WORDS, 3)),
        'data': {
            'x': random.randint(1, 9),
            'y': random.randint(100, 999),
            'z': random.randint(10000, 99999),
            'range': list(range(random.randint(10, 50))),
        },
    }


@pytest.fixture
def rt1():
    return rh.RedThing('test', 'rt1')


@pytest.fixture
def rt2():
    return rh.RedThing('test', 'rt2', json_fields='data')


@pytest.fixture
def rt3():
    return rh.RedThing('test', 'rt3', index_fields='a', json_fields='data')


@pytest.fixture
def rt4():
    return rh.RedThing('test', 'rt4', index_fields='a,b,c')


@pytest.mark.skipif(DBSIZE != 0, reason='Database is not empty, has {} item(s)'.format(DBSIZE))
@pytest.mark.skipif(REDIS_CONNECTED is False, reason='Not connected to redis')
class TestRedThing:
    @classmethod
    def teardown_class(cls):
        _rt1 = rt1()
        _rt2 = rt2()
        _rt3 = rt3()
        _rt4 = rt4()
        _rt1.clear_keyspace()
        _rt2.clear_keyspace()
        _rt3.clear_keyspace()
        _rt4.clear_keyspace()
        rh.REDIS.delete('RedThing')

    def test_add_and_get(self, rt1):
        data = generate_rt1_data()
        hash_id = rt1.add(**data)
        retrieved = rt1.get(hash_id)
        assert retrieved == data

    def test_add_and_get_some(self, rt1):
        data = generate_rt1_data()
        hash_id = rt1.add(**data)
        retrieved = rt1.get(hash_id, 'x,y')
        assert retrieved == {k: v for k, v in data.items() if k in ('x', 'y')}

    def test_add_and_get_one(self, rt1):
        data = generate_rt1_data()
        hash_id = rt1.add(**data)
        retrieved = rt1.get(hash_id, 'x')
        assert retrieved == {'x': data['x']}

    def test_add_and_get_with_json(self, rt2):
        data = generate_rt23_data()
        hash_id = rt2.add(**data)
        retrieved = rt2.get(hash_id)
        assert retrieved == data

    def test_add_and_get_with_index(self, rt3):
        data = generate_rt23_data()
        hash_id = rt3.add(**data)
        retrieved = rt3.get(hash_id)
        assert retrieved == data

    def test_add_multiple_and_size(self, rt3):
        for _ in range(19):
            rt3.add(**generate_rt23_data())

        assert rt3.size == 20

    def test_find(self, rt4):
        rt4.add(a='red', b='circle', c='striped')
        rt4.add(a='red', b='square', c='plain')
        rt4.add(a='green', b='triangle', c='spotted')
        rt4.add(a='yellow', b='triangle', c='spotted')
        rt4.add(a='yellow', b='triangle', c='spotted')
        rt4.add(a='red', b='triangle', c='plain')
        rt4.add(a='red', b='square', c='spotted')
        rt4.add(a='green', b='square', c='striped')
        rt4.add(a='blue', b='circle', c='striped')
        rt4.add(a='blue', b='square', c='plain')

        assert len(rt4.find()) == 10
        assert len(rt4.find(limit=5)) == 5
        assert rt4.find('a:blue', count=True) == 2
        assert rt4.find('a:red,a:yellow', count=True) == 6
        assert len(rt4.find('a:red,a:yellow', limit=3)) == 3
        assert rt4.find('b:triangle,c:spotted', count=True) == 3
        assert rt4.find('b:triangle,b:square,c:striped,c:plain', count=True) == 4
        assert rt4.find('a:red,b:triangle,b:square,c:spotted,c:plain', count=True) == 3

    def test_delete(self, rt4):
        reds = rt4.find('a:red')
        assert rt4.size == 10
        assert len(reds) == 4
        assert rh.REDIS.zscore('test:rt4:a', 'red') == 4.0
        a_red_id = reds[0]['_id']
        a_red = rt4.get(a_red_id)
        b_field = a_red['b']
        b_count = rh.REDIS.zscore('test:rt4:b', b_field)
        rt4.delete(a_red_id)
        reds = rt4.find('a:red')
        assert rh.REDIS.zscore('test:rt4:a', 'red') == 3.0
        assert rt4.size == 9
        assert len(reds) == 3
        assert rh.REDIS.zscore('test:rt4:b', b_field) == b_count - 1
        assert rt4.get(a_red_id) == {}

    def test_update(self, rt4):
        reds = rt4.find('a:red')
        assert rh.REDIS.zscore('test:rt4:a', 'red') == 3.0
        assert rh.REDIS.zscore('test:rt4:a', 'blue') == 2.0
        assert len(reds) == 3
        assert rt4.size == 9
        a_red_id = reds[0]['_id']
        rt4.update(a_red_id, a='blue')
        reds = rt4.find('a:red')
        assert rh.REDIS.zscore('test:rt4:a', 'blue') == 3.0
        assert len(reds) == 2
        assert rt4.get(a_red_id)['a'] == 'blue'

    def test_base_key(self, rt1, rt2, rt3, rt4):
        rt1._base_key == 'test:rt1'
        rt2._base_key == 'test:rt2'
        rt3._base_key == 'test:rt3'
        rt4._base_key == 'test:rt4'

    def test_keyspace_in_use(self, rt1, rt2, rt3, rt4):
        assert rh.REDIS.dbsize() > 0
        assert rt1.size > 0
        assert rt2.size > 0
        assert rt3.size > 0
        assert rt4.size > 0
