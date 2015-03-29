def setup(bot):
    bot.config.add_section('linktracker')
    if not bot.config.civ.get_list('games'):
        bot.config.civ.games = []
        bot.config.save()
