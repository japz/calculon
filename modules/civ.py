from __future__ import unicode_literals
from bs4 import BeautifulSoup
from willie import web
import willie.module
import re

_NAME = 'civ'
_BASE = 'http://multiplayerrobot.com/Game/Details?id='

def setup(bot):
    bot.config.add_section('civ')
    if not bot.config.civ.get_list('games'):
        bot.config.civ.games = []
        bot.config.save()


def fetch_game(game_id):
    uri = _BASE + game_id
    headers = {'Content-Length': '0'}
    data = web.post(uri, headers)
    soup = BeautifulSoup(data)
    data = {'id': game_id,
            'active_player': soup.find(class_='game-host').find(class_='avatar').attrs['title'],
            'turn_timer': soup.find(id='turn-timer-container').find('strong').string}

    return data

def add_game(bot, game_id):
    if not re.match('^[0-9]+$', game_id):
        bot.say('Game ID must be an integer')
        return
    if game_id in bot.config.civ.games:
        bot.say('Already tracking game ' + game_id)
        return

    data = fetch_game(game_id)
    if not data['active_player']:
        bot.say('Game is not active')
        return

    bot.config.civ.games.append(game_id)
    bot.config.save()
    bot.say('Game {id} with active player {active_player} added'.format(**data))


def del_game(bot, game_id):
    if game_id not in bot.config.civ.games:
        bot.say('Game ID {} unknown'.format(game_id))
    else:
        bot.config.civ.games.remove(game_id)
        bot.config.save()
        bot.say('Deleted game ' + game_id)

def list_games(bot):
    if not bot.config.civ.get_list('games'):
        bot.say('No games configured')
    else:
        for game in bot.config.civ.get_list('games'):
            bot.say('Game {id}: Active player is {active_player}, turn ends on {turn_timer}'.format(**fetch_game(game)))


@willie.module.commands('civ')
@willie.module.example('.civ [{add|del} <game-id>]')
def civ(bot, trigger):
    '''Civilization 5 MPR game info'''

    if not trigger.group(2):
        list_games(bot)
        return

    command, _, params = trigger.group(2).partition(' ')

    if command == 'add':
        add_game(bot, params)
    elif command == 'del' or command == 'delete':
        del_game(bot, params)
    else:
        bot.say('Command {} invalid'.format(command))


