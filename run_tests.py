import asyncio

from bot.tests import test_game

loop = asyncio.get_event_loop()
# loop.run_until_complete(test_game.test_cardgame())
loop.run_until_complete(test_game.test_songgame())