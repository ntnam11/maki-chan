import subprocess
import bot
import gc
import discord
import asyncio
import time

from bot.exceptions import ConfigException

async def run():
    try:
        from bot.client import MainClient
        from bot.opus_loader import load_opus_lib
        
        client = MainClient()
        client.load_config()
        load_opus_lib()

        if not client.prefix:
            print('Prefix is not supported. Please choose a different one')
            raise ConfigException
            
        try:
            await client.start(client.token)
        except discord.LoginFailure:
            print('No Token specified. Exiting...')
            raise ConfigException
        except ConfigException:
            raise
        except Exception as e:
            import traceback
            print(e)
            traceback.print_exc()

    except ImportError:
        subprocess.call('pip install requirements.txt')
        return 0

def main():
    retry = True
    retry_count = 0
    while retry:
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(run())
        except ConfigException:
            retry = False
            exit()

        gc.collect()
        asyncio.set_event_loop(asyncio.get_event_loop())
        retry_count += 1
        timeout = min(retry_count * 2, 30)
        print(f'Restarting in {timeout} seconds...')
        time.sleep(timeout)

if __name__ == '__main__':
    main()