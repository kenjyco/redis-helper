import logging
import random
import os.path
import input_helper as ih
import redis_helper as rh
from functools import partial
from enum import Enum


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


PLAYERS = rh.Collection(
    'mmo',
    'player',
    unique_field='handle',
    index_fields='email, status',
    insert_ts=True
)

CHARACTERS = rh.Collection(
    'mmo',
    'character',
    unique_field='name',
    index_fields='species, specialty, rank, player, status',
    insert_ts=True
)

ITEMS = rh.Collection(
    'mmo',
    'item',
    unique_field='name',
)

MESSAGES = rh.Collection(
    'mmo',
    'message',
    index_fields='to, from',
)


class character_status(Enum):
    full_health = 1
    medium_health = 2
    low_health = 3
    critical_health = 4
    dead = 5
    un_dead = 6


class Player(object):
    """A specific human that is playing the game"""
    def __init__(self, handle, **kwargs):
        self._collection = PLAYERS
        _handle = handle.replace(' ', '_').lower()


class CharacterController(object):
    """Controlls a particular character"""
    x_positions = 'mmo:positions:x'
    y_positions = 'mmo:positions:y'

    @classmethod
    def move_right(cls, character_name, n=1, log=True):
        """Move 'character_name' right 'n' spaces and log"""
        if isinstance(n, (int, float)):
            rh.REDIS.hincrbyfloat(cls.x_positions, character_name, n)
            if log:
                logger.info('Character {} moved right by {}'.format(character_name, n))
        elif log:
            logger.error('Character {} cannot move right by {}'.format(character_name, repr(n)))

    @classmethod
    def move_left(cls, character_name, n=1, log=True):
        """Move 'character_name' left 'n' spaces and log"""
        if isinstance(n, (int, float)):
            rh.REDIS.hincrbyfloat(cls.x_positions, character_name, -1 * n)
            if log:
                logger.info('Character {} moved left by {}'.format(character_name, n))
        elif log:
            logger.error('Character {} cannot move left by {}'.format(character_name, repr(n)))

    @classmethod
    def move_up(cls, character_name, n=1, log=True):
        """Move 'character_name' up 'n' spaces and log"""
        if isinstance(n, (int, float)):
            rh.REDIS.hincrbyfloat(cls.y_positions, character_name, n)
            if log:
                logger.info('Character {} moved up by {}'.format(character_name, n))
        elif log:
            logger.error('Character {} cannot move up by {}'.format(character_name, repr(n)))

    @classmethod
    def move_down(cls, character_name, n=1, log=True):
        """Move 'character_name' down 'n' spaces and log"""
        if isinstance(n, (int, float)):
            rh.REDIS.hincrbyfloat(cls.y_positions, character_name, -1 * n)
            if log:
                logger.info('Character {} moved down by {}'.format(character_name, n))
        elif log:
            logger.error('Character {} cannot move down by {}'.format(character_name, repr(n)))

    @classmethod
    def go(cls, character_name, x, y, log=True):
        """Move 'character_name' to a specific location"""
        errors = []
        if not isinstance(x, (int, float)):
            errors.append('Invalid x value: {}'.format(repr(x)))
        if not isinstance(y, (int, float)):
            errors.append('Invalid y value: {}'.format(repr(y)))

        if not errors:
            pipe = rh.REDIS.pipeline()
            pipe.hset(cls.x_positions, character_name, x)
            pipe.hset(cls.y_positions, character_name, y)
            pipe.execute()
            if log:
                logger.info('Character {} moved to ({}, {})'.format(character_name, x, y))
        elif log:
            logger.error(' | '.join(errors))

    @classmethod
    def get_position(cls, character_name, log=True):
        """Log current position for character_name and return coordinates as a dict"""
        position = {
            'x': ih.decode(rh.REDIS.hget(cls.x_positions, character_name)) or 0,
            'y': ih.decode(rh.REDIS.hget(cls.y_positions, character_name)) or 0,
        }
        if log:
            logger.info('Character {} is at position ({}, {})'.format(
                character_name,
                position['x'],
                position['y']
            ))
        return position


try:
    from chloop import GetCharLoop
except ImportError:
    logger.error('Install "chloop" package to this virtual environment to run the gameloop')
    GameLoop = None
    gameloop = None
else:
    class GameLoop(GetCharLoop):
        def __init__(self, *args, **kwargs):
            self._character_name = kwargs.pop('character_name', '')
            self._display_name = kwargs.pop('display_name', '')
            super().__init__(*args, **kwargs)
            self._validate()

        def _validate(self):
            """Make sure everything is as it should be"""
            errors = []
            if not self._character_name:
                errors.append('No character_name provided')
            elif ' ' in self._character_name:
                errors.append('There are spaces in the character_name {}'.format(repr(self._character_name)))

            if errors:
                raise Exception('\n'.join(errors))

        def info(self):
            """Print/return character info"""
            i = {
                'display_name': self._display_name,
                'character_name': self._character_name,
                'position': CharacterController.get_position(self._character_name, log=False)
            }
            logger.info('Character {} ({}) is at position ({}, {})'.format(
                i['character_name'],
                i['display_name'],
                i['position']['x'],
                i['position']['y']
            ))
            return i

        def go(self, *args):
            """Move to a specific location"""
            x = None
            y = None
            if len(args) == 2:
                x, y = args
                x = ih.from_string(x)
                y = ih.from_string(y)
                CharacterController.go(self._character_name, x, y)
            else:
                logger.error('You must specify an x and y coordinate, not {}'.format(repr(args)))

        def random(self):
            """Move to a random position"""
            CharacterController.go(
                self._character_name,
                random.randint(-1000, 1000),
                random.randint(-1000, 1000)
            )

        def left(self, n):
            """Move left n units"""
            CharacterController.move_left(self._character_name, ih.from_string(n))

        def right(self, n):
            """Move right n units"""
            CharacterController.move_right(self._character_name, ih.from_string(n))

        def up(self, n):
            """Move up n units"""
            CharacterController.move_up(self._character_name, ih.from_string(n))

        def down(self, n):
            """Move down n units"""
            CharacterController.move_down(self._character_name, ih.from_string(n))


if GameLoop:
    display_name = ih.user_input('\nWhat is the character name')
    character_name = display_name.replace(' ', '_').lower()

    # Keyboard shortcuts that work when the gameloop is running
    chfunc = {
        'h': (partial(CharacterController.move_left, character_name, 2), 'move left 2 units'),
        'l': (partial(CharacterController.move_right, character_name, 2), 'move right 2 units'),
        'k': (partial(CharacterController.move_up, character_name, 2), 'move up 2 units'),
        'j': (partial(CharacterController.move_down, character_name, 2), 'move down 2 units'),
        'H': (partial(CharacterController.move_left, character_name, 5), 'move left 5 units'),
        'L': (partial(CharacterController.move_right, character_name, 5), 'move right 5 units'),
        'K': (partial(CharacterController.move_up, character_name, 5), 'move up 5 units'),
        'J': (partial(CharacterController.move_down, character_name, 5), 'move down 5 units'),
        '\x1b[D': (partial(CharacterController.move_left, character_name, 1), '(left arrow) move left 1 unit'),
        '\x1b[C': (partial(CharacterController.move_right, character_name, 1), '(right arrow) move right 1 unit'),
        '\x1b[A': (partial(CharacterController.move_up, character_name, 1), '(up arrow) move up 1 unit'),
        '\x1b[B': (partial(CharacterController.move_down, character_name, 1), '(down arrow) move down 1 unit'),
        'p': (partial(CharacterController.get_position, character_name), 'current position'),
    }
    gameloop = GameLoop(
        chfunc_dict=chfunc,
        prompt='game-repl> ',
        name='mygame',
        character_name=character_name,
        display_name=display_name,
    )


if __name__ == '__main__':
    if GameLoop:
        logger.info('Starting the gameloop...')
        gameloop()
    else:
        logger.info('Explore the following objects: PLAYERS, CHARACTERS, ITEMS, MESSAGES, Player, CharacterController')
