import subprocess
import bot
import gc
import discord
import asyncio
import time
import logging.config
import logging

from bot.exceptions import *

logging.getLogger('websockets.protocol').setLevel('INFO')
logging.getLogger('PIL.PngImagePlugin').setLevel('INFO')
logging.getLogger('discord.gateway').setLevel('INFO')
logging.getLogger('discord.http').setLevel('INFO')
logging.getLogger('discord.client').setLevel('INFO')

logger = logging.getLogger('root')

async def run():
    try:
        from bot.client import MainClient
        from bot.opus_loader import load_opus_lib
        
        client = MainClient()
        client.load_config()
        logging.config.dictConfig(client.logging)
        load_opus_lib()

        if not client.prefix:
            logger.error('Prefix is not supported. Please choose a different one')
            raise ConfigException
            
        try:
            await client.start(client.token)
        except discord.LoginFailure:
            logger.error('No Token specified. Exiting...')
            raise ConfigException
        except ConfigException:
            raise
        except TypeError:
            raise SleepException
        except Exception as e:
            import traceback
            logger.error(e)
            traceback.print_exc()

    except ImportError as e:
        subprocess.run('pip install -r requirements.txt'.split(' '))
        return 0

def main():
    retry = True
    retry_count = 0
    while retry:
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(run())
        except (ConfigException, SleepException):
            retry = False
            exit()
        except RestartSignal:
            pass

        gc.collect()
        asyncio.set_event_loop(asyncio.get_event_loop())
        retry_count += 1
        timeout = min(retry_count * 2, 30)
        logger.error(f'Restarting in {timeout} seconds...')
        time.sleep(timeout)

if __name__ == '__main__':
    main()