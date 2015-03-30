from __future__ import unicode_literals
from bs4 import BeautifulSoup
from willie import tools, web
import copy
import willie.module
import re
import time

_NAME = 'civ'
_BASE = 'http://multiplayerrobot.com/Game/Details?id='
_INTERVAL = 300

def setup(bot):
    bot.config.add_section('civ')
    if not bot.config.civ.get_list('games'):
        bot.config.civ.games = []
        bot.config.save()
    if not bot.config.civ.get_list('announce_channels'):
        bot.config.civ.announce_channels = []
        bot.config.save()
    if not bot.memory.contains('civ_game_status'):
        bot.memory['civ_game_status'] = {}
    if not bot.memory.contains('civ_update_lock'):
        bot.memory['civ_update_lock'] = {'_global': False}


def fetch_game(game_id):
    try:
        uri = _BASE + game_id
        headers = {'Content-Length': '0'}
        data = web.post(uri, headers)
        soup = BeautifulSoup(data)
        data = {'id': game_id,
                'active_player': soup.find(class_='game-host').find(class_='avatar').attrs['title'],
                'turn_timer': soup.find(id='turn-timer-container').find('strong').string}
    except Exception as e:
        return e

    return data


def update_games(bot, wait=False):
    if bot.memory['civ_update_lock']['_global']:
        if not wait:
            return False
        while bot.memory['civ_update_lock']['_global']:
            time.sleep(1)
        return True
    bot.memory['civ_update_lock']['_global'] = True

    try:
        for game in bot.config.civ.get_list('games'):
            data = fetch_game(game)
            if isinstance(data, Exception):
                bot.memory['civ_game_status'][game] = data
            elif game not in bot.memory['civ_game_status']:
                data['updated'] = time.time()
                bot.memory['civ_game_status'][game] = data
            else:
                old_data = bot.memory['civ_game_status'][game]
                if old_data['active_player'] != data['active_player'] or old_data['turn_timer'] != data['turn_timer']:
                    data['updated'] = time.time()
                    bot.memory['civ_game_status'][game] = data

    except Exception:
        raise
    finally:
        bot.memory['civ_update_lock']['_global'] = False
    return True


def add_game(bot, game_id):
    if not re.match('^[0-9]+$', game_id):
        bot.say('Game ID must be an integer')
        return
    if game_id in bot.config.civ.games:
        bot.say('Already tracking game ' + game_id)
        return

    data = fetch_game(game_id)

    try:
        _ = data['active_player']
    except:
        bot.reply('Game is not active')
        return

    data['updated'] = time.time()

    bot.config.civ.games.append(game_id)
    bot.config.save()
    bot.say('Game {id} with active player {active_player} added'.format(**data))


def del_game(bot, game_id):
    if game_id not in bot.config.civ.games:
        bot.reply('Game ID {} unknown'.format(game_id))
    else:
        bot.config.civ.games.remove(game_id)
        bot.config.save()
        bot.reply('Deleted game ' + game_id)


def list_games(bot):
    if not bot.config.civ.get_list('games'):
        bot.say('No games configured')
        return
    bot.say('Active games: ' + ', '.join(sorted(bot.config.civ.get_list('games'))))


def game_status(bot, trigger):
    if not bot.config.civ.get_list('games'):
        bot.reply('No games configured')
        return
    if trigger.sender in bot.memory['civ_update_lock']:
        bot.reply('Already fetching game status for {}, please be patient.'.format(bot.memory['civ_update_lock'][trigger.sender]))
        return
    bot.memory['civ_update_lock'][trigger.sender] = trigger.nick

    update_games(bot, wait=True)

    for game in sorted(bot.config.civ.get_list('games')):
        data = bot.memory['civ_game_status'][game]
        if isinstance(data, Exception):
            text_bit = 'Game {}: Error fetching status: {}'.format(game, data)
        else:
            text_bit = 'Game {id}: Active player is {active_player}, turn ends on {turn_timer}'.format(**data)
        bot.say(text_bit)
    del(bot.memory['civ_update_lock'][trigger.sender])


@willie.module.commands('civ')
@willie.module.example('.civ [{add|del} <game-id>]')
def civ(bot, trigger):
    '''Civilization 5 MPR game info'''

    if not trigger.group(2):
        game_status(bot, trigger)
        return

    command, _, params = trigger.group(2).partition(' ')

    if command == 'add':
        add_game(bot, params)
    elif command == 'del' or command == 'delete':
        del_game(bot, params)
    elif command == 'list':
        list_games(bot)
    elif command == 'unlock':
        if not trigger.admin:
            return
        bot.memory['civ_update_lock'] = {'_global': False}
        bot.reply('done')
    else:
        bot.say('Command {} invalid'.format(command))


@willie.module.interval(_INTERVAL)
def interval_update_games(bot):
    if len(bot.config.civ.announce_channels) == 0:
        return
    update_games(bot, wait=True)
    status = bot.memory['civ_game_status']
    for game in bot.config.civ.get_list('games'):
        game_status = status[game]
        if isinstance(game_status, Exception):
            continue
        if time.time() - game_status['updated'] < _INTERVAL:
            for chan in bot.config.civ.get_list('announce_channels'):
                bot.msg(chan, 'Game {id} TURN! New active player is {active_player}, turn ends on {turn_timer}'.format(**game_status))
