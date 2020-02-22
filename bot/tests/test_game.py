import asyncio

from .base import *
from ..games import Games

async def wait_for(*args, **kwargs):
    return DiscordMessage('Wait for incoming message')

async def test_cardgame():
    message = DiscordMessage()
    bot_instance = Games()
    bot_instance.playing_cardgame = False
    bot_instance.wait_for = wait_for

    card_num = 10

    await bot_instance.cmd_cardgame(message, card_num)

async def test_songgame():
    message = DiscordMessage()
    bot_instance = Games()
    bot_instance.playing_songgame = False
    bot_instance.wait_for = wait_for

    await bot_instance.cmd_songgame(message, 5)