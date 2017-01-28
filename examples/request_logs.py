import redis_helper as rh
import random
import time
from pprint import pprint


request_logs = rh.RedThing(
    'log',
    'request',
    index_fields='status,uri,host',
    json_fields='request,response,headers'
)


def generate_request_log(add=True, show=False):
    """Generate a request_log dict

    - add: if True, automatically add the genarated request_log to 'request_logs'
    - show: if True, pprint the generated data to the screen
    """
    request_log = {
        'method': random.choice(['get', 'post']),
        'status': random.choice([200] * 1500 + [400]),
        'host': random.choice(['dogs.com', 'cats.com', 'birds.com', 'tigers.com']),
        'uri': random.choice(['/colors', '/shapes', '/breeds', '/search']),
    }

    if request_log['method'] == 'get':
        request_log['querystring'] = '?x={}&y={}'.format(
            random.randint(0,9),
            random.randint(100, 999)
        )

    if request_log['status'] == 400:
        request_log['request'] = {
            'blah1': 'something',
            'blah2': 'something else',
            'blah3': [1, 2, 3],
        }
        request_log['error'] = 'something ' + random.choice([
            'bad', 'awful', 'terrible', 'critical', 'serious', 'scary'
        ])

    _id = None
    if add:
        _id = request_logs.add(**request_log)
    if show:
        pprint(request_log, width=120)

    return (_id, request_log)


def slow_trickle_requests(sleeptime=.234, show=False, randomsleep=False):
    """Slowly generate request_logs and add to 'request_logs'

    - sleeptime: an exact time to sleep between generating each request_log
    - show: if True, pprint the generated data to the screen
    - randomsleep: if True, choose a random sleep duration between 0 and 1 sec
      after generating each request_log
    """
    sleeper = lambda: time.sleep(sleeptime)
    if randomsleep:
        sleeper = lambda: time.sleep(random.random())
    while True:
        try:
            generate_request_log(add=True, show=show)
            sleeper()
        except KeyboardInterrupt:
            break


if __name__ == '__main__':
    if request_logs.size == 0:
        print('\nRun `slow_trickle_requests(randomsleep=True, show=True)` in another terminal')
    else:
        print('\nrequest_logs size:', request_logs.size)
        print('\nTop 3 index values per index:')
        pprint(request_logs.index_field_info(3))
