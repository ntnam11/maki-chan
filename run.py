import logging
import subprocess

def run():
    try:
        from client import MainClient
        
        client = MainClient()
        client.load_config()
        if not client.prefix:
            print('Prefix is not supported. Please choose a different one')
            exit()
            
        try:
            client.run(client.token)
        except AttributeError:
            print('No Token specified. Exiting...')
            exit()

        return True

    except ImportError:
        subprocess.call('pip install requirements.txt')
        return False

while True:
    r = run()
    if r:
        break