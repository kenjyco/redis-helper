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


def generate_coll1_data():
    return {
        'x': random.randint(1, 9),
        'y': random.randint(100, 999),
        'z': random.randint(10000, 99999),
    }


def generate_coll23_data():
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
def coll1():
    return rh.Collection('test', 'coll1')


@pytest.fixture
def coll2():
    return rh.Collection('test', 'coll2', json_fields='data')


@pytest.fixture
def coll3():
    return rh.Collection('test', 'coll3', index_fields='a', json_fields='data')


@pytest.fixture
def coll4():
    return rh.Collection('test', 'coll4', index_fields='a,b,c')


@pytest.mark.skipif(DBSIZE != 0, reason='Database is not empty, has {} item(s)'.format(DBSIZE))
@pytest.mark.skipif(REDIS_CONNECTED is False, reason='Not connected to redis')
class TestCollection:
    @classmethod
    def teardown_class(cls):
        _coll1 = coll1()
        _coll2 = coll2()
        _coll3 = coll3()
        _coll4 = coll4()
        _coll1.clear_keyspace()
        _coll2.clear_keyspace()
        _coll3.clear_keyspace()
        _coll4.clear_keyspace()
        rh.REDIS.delete('_REDIS_HELPER_COLLECTION')

    def test_add_and_get(self, coll1):
        data = generate_coll1_data()
        hash_id = coll1.add(**data)
        retrieved = coll1.get(hash_id)
        assert retrieved == data

    def test_add_and_get_some(self, coll1):
        data = generate_coll1_data()
        hash_id = coll1.add(**data)
        retrieved = coll1.get(hash_id, 'x,y')
        assert retrieved == {k: v for k, v in data.items() if k in ('x', 'y')}

    def test_add_and_get_one(self, coll1):
        data = generate_coll1_data()
        hash_id = coll1.add(**data)
        retrieved = coll1.get(hash_id, 'x')
        assert retrieved == {'x': data['x']}

    def test_add_and_get_with_json(self, coll2):
        data = generate_coll23_data()
        hash_id = coll2.add(**data)
        retrieved = coll2.get(hash_id)
        assert retrieved == data

    def test_add_and_get_with_index(self, coll3):
        data = generate_coll23_data()
        hash_id = coll3.add(**data)
        retrieved = coll3.get(hash_id)
        assert retrieved == data

    def test_add_multiple_and_size(self, coll3):
        for _ in range(19):
            coll3.add(**generate_coll23_data())

        assert coll3.size == 20

    def test_find(self, coll4):
        coll4.add(a='red', b='circle', c='striped')
        coll4.add(a='red', b='square', c='plain')
        coll4.add(a='green', b='triangle', c='spotted')
        coll4.add(a='yellow', b='triangle', c='spotted')
        coll4.add(a='yellow', b='triangle', c='spotted')
        coll4.add(a='red', b='triangle', c='plain')
        coll4.add(a='red', b='square', c='spotted')
        coll4.add(a='green', b='square', c='striped')
        coll4.add(a='blue', b='circle', c='striped')
        coll4.add(a='blue', b='square', c='plain')

        assert len(coll4.find()) == 10
        assert len(coll4.find(limit=5)) == 5
        assert coll4.find('a:blue', count=True) == 2
        assert coll4.find('a:red,a:yellow', count=True) == 6
        assert len(coll4.find('a:red,a:yellow', limit=3)) == 3
        assert coll4.find('b:triangle,c:spotted', count=True) == 3
        assert coll4.find('b:triangle,b:square,c:striped,c:plain', count=True) == 4
        assert coll4.find('a:red,b:triangle,b:square,c:spotted,c:plain', count=True) == 3

    def test_delete(self, coll4):
        reds = coll4.find('a:red')
        assert coll4.size == 10
        assert len(reds) == 4
        assert rh.REDIS.zscore('test:coll4:a', 'red') == 4.0
        a_red_id = reds[0]['_id']
        a_red = coll4.get(a_red_id)
        b_field = a_red['b']
        b_count = rh.REDIS.zscore('test:coll4:b', b_field)
        coll4.delete(a_red_id)
        reds = coll4.find('a:red')
        assert rh.REDIS.zscore('test:coll4:a', 'red') == 3.0
        assert coll4.size == 9
        assert len(reds) == 3
        assert rh.REDIS.zscore('test:coll4:b', b_field) == b_count - 1
        assert coll4.get(a_red_id) == {}

    def test_update(self, coll4):
        reds = coll4.find('a:red')
        assert rh.REDIS.zscore('test:coll4:a', 'red') == 3.0
        assert rh.REDIS.zscore('test:coll4:a', 'blue') == 2.0
        assert len(reds) == 3
        assert coll4.size == 9
        a_red_id = reds[0]['_id']
        coll4.update(a_red_id, a='blue')
        reds = coll4.find('a:red')
        assert rh.REDIS.zscore('test:coll4:a', 'blue') == 3.0
        assert len(reds) == 2
        assert coll4.get(a_red_id)['a'] == 'blue'

    def test_base_key(self, coll1, coll2, coll3, coll4):
        coll1._base_key == 'test:coll1'
        coll2._base_key == 'test:coll2'
        coll3._base_key == 'test:coll3'
        coll4._base_key == 'test:coll4'

    def test_keyspace_in_use(self, coll1, coll2, coll3, coll4):
        assert rh.REDIS.dbsize() > 0
        assert coll1.size > 0
        assert coll2.size > 0
        assert coll3.size > 0
        assert coll4.size > 0
