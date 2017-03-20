import logging
import os.path
import redis_helper as rh


LOGFILE = os.path.abspath('log--mmorpg-game.log')
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

players = rh.Collection(
    'mmo',
    'player',
    unique_field='handle',
    index_fields='email,status',
    insert_ts=True
)

characters = rh.Collection(
    'mmo',
    'character',
    unique_field='name',
    index_fields='species,specialty,rank,player,status',
    insert_ts=True
)

items = rh.Collection(
    'mmo',
    'item',
    unique_field='name',
)

messages = rh.Collection(
    'mmo',
    'message',
    index_fields='to,from',
)
