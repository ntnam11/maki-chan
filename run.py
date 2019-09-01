import logging
import subprocess
import os
import bot
import gc

def run():
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
            client.run(client.token)
        except Exception as e:
            print('No Token specified. Exiting...')
            exit()

    except ImportError:
        subprocess.call('pip install requirements.txt')
        run()

run()