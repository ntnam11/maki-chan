import logging
import subprocess
import os
import bot
import gc
import discord
import asyncio

async def run():
    try:
        from bot.client import MainClient
        from bot.opus_loader import load_opus_lib
        
        client = MainClient()
        client.load_config()
        load_opus_lib()

        if not client.prefix:
            print('Prefix is not supported. Please choose a different one')
            exit()
            
        try:
            await client.start(client.token)
        except discord.LoginFailure:
            print('No Token specified. Exiting...')
            exit()
        except Exception as e:
            pass

    except ImportError:
        subprocess.call('pip install requirements.txt')
        await run()

loop = asyncio.get_event_loop()
loop.run_until_complete(run())
