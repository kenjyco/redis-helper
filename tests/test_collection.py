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
    return rh.Collection('test', 'coll4', index_fields='a, b, c')


@pytest.fixture
def coll5():
    return rh.Collection('test', 'coll5', unique_field='name', index_fields='status')


@pytest.fixture
def coll6():
    return rh.Collection('test', 'coll6', reference_fields='thing--test:coll5',
                         index_fields='z')


@pytest.mark.skipif(DBSIZE != 0, reason='Database is not empty, has {} item(s)'.format(DBSIZE))
@pytest.mark.skipif(REDIS_CONNECTED is False, reason='Not connected to redis')
class TestCollection:
    @classmethod
    def teardown_class(cls):
        _coll1 = coll1()
        _coll2 = coll2()
        _coll3 = coll3()
        _coll4 = coll4()
        _coll5 = coll5()
        _coll6 = coll6()
        _coll1.clear_keyspace()
        _coll2.clear_keyspace()
        _coll3.clear_keyspace()
        _coll4.clear_keyspace()
        _coll5.clear_keyspace()
        _coll6.clear_keyspace()
        rh.REDIS.delete('_REDIS_HELPER_COLLECTION')

    def test_add_and_get(self, coll1):
        data = generate_coll1_data()
        hash_id = coll1.add(**data)
        retrieved = coll1.get(hash_id)
        assert retrieved == data

    def test_add_and_get_some(self, coll1):
        data = generate_coll1_data()
        hash_id = coll1.add(**data)
        retrieved = coll1.get(hash_id, 'x, y')
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

    def test_add_and_get_with_unique(self, coll5):
        hash_id = coll5.add(name='first', x=5, y=10, status='ok')
        assert coll5[-1]['name'] == 'first'
        with pytest.raises(AssertionError):
            coll5.add(name='first', x=10, y=100, status='ok')
        with pytest.raises(AssertionError):
            coll5.add(x=10, y=100, status='ok')
        coll5.add(name='second', x=10, y=100, status='ok')
        assert coll5['first'] == coll5.get(hash_id, include_meta=True)

    def test_add_and_get_with_reference(self, coll5, coll6):
        hash_id = coll6.add(thing='first', z=100, misc='sure')
        thing = coll6.get(hash_id, 'thing')['thing']
        thing_with_ref_data = coll6.get(hash_id, 'thing', load_ref_data=True)['thing']
        first_from_coll5 = coll5['first']
        assert thing == 'first'
        assert thing_with_ref_data == first_from_coll5

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
        assert coll4.find('a:red, a:yellow', count=True) == 6
        assert len(coll4.find('a:red, a:yellow', limit=3)) == 3
        assert coll4.find('b:triangle, c:spotted', count=True) == 3
        assert coll4.find('b:triangle, b:square, c:striped, c:plain', count=True) == 4
        assert coll4.find('a:red, b:triangle, b:square, c:spotted, c:plain', count=True) == 3

    def test_delete(self, coll4):
        reds = coll4.find('a:red')
        assert coll4.size == 10
        assert len(reds) == 4
        assert rh.REDIS.zscore('test:coll4:a', 'red') == 4.0
        a_red_id = reds[0]['_id']
        a_red = coll4.get(a_red_id)
        assert a_red_id in coll4.get_stats()['counts']
        b_field = a_red['b']
        b_count = rh.REDIS.zscore('test:coll4:b', b_field)
        coll4.delete(a_red_id)
        assert a_red_id not in coll4.get_stats()['counts']
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

    def test_delete_where(self, coll4):
        assert coll4.size == 9
        assert coll4.top_values_for_index('a', 2) == [('blue', 3), ('yellow', 2)]
        assert coll4.find('a:blue', count=True) == 3
        found = coll4.find('a:blue', limit=1)
        assert found and len(found) == 1
        coll4.delete_where('a:blue', limit=2)
        assert coll4.find('a:blue', count=True) == 1

    def test_delete_where_limit(self, coll4):
        assert coll4.size == 7
        assert coll4.top_values_for_index('a', 2) == [('yellow', 2), ('red', 2)]
        assert coll4.find(limit=2, desc=False, item_format='{_id}') == [
            'test:coll4:1', 'test:coll4:2'
        ]
        coll4.delete_where(limit=2)
        assert coll4.find(limit=2, desc=False, item_format='{_id}') == [
            'test:coll4:3', 'test:coll4:4'
        ]

    def test_delete_many(self, coll4):
        assert coll4.size == 5
        three_ids = random.sample(coll4.find(item_format='{_id}'), 3)
        one_id = random.choice(three_ids)
        one_data = coll4.get(one_id)
        assert one_data != {}
        coll4.delete_many(*three_ids)
        one_data = coll4.get(one_id)
        assert one_data == {}
        assert coll4.size == 2

    def test_base_key(self, coll1, coll2, coll3, coll4, coll5, coll6):
        coll1._base_key == 'test:coll1'
        coll2._base_key == 'test:coll2'
        coll3._base_key == 'test:coll3'
        coll4._base_key == 'test:coll4'
        coll5._base_key == 'test:coll5'
        coll6._base_key == 'test:coll6'

    def test_keyspace_in_use(self, coll1, coll2, coll3, coll4, coll5, coll6):
        assert rh.REDIS.dbsize() > 0
        assert coll1.size > 0
        assert coll2.size > 0
        assert coll3.size > 0
        assert coll4.size > 0
        assert coll5.size > 0
        assert coll6.size > 0
