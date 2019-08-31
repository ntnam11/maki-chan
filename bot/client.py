import os
import logging
import asyncio
import yaml
import shutil
from textwrap import dedent

import discord

from .commands import Commands, _pic_func

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s]: %(message)s'))
logger.addHandler(handler)

class MainClient(discord.Client, discord.VoiceClient, Commands):
    def __init__(self):
        self.load_config()

        for attr in self.config:
            setattr(self, attr, self.config[attr])
        
        self.playing_cardgame = False
        self.voice_channel = None
        self.music_queue = []
        self.current_song = None
        self.voice_text_channel = None
        self.music_cache_dir = os.path.join(os.getcwd(), 'audio_cache')

        pic_cmds = {
            'cmd_hug': {
                'type': 'hug',
                'target': True,
                'text': 'hugs'
            },
            'cmd_cry': {
                'type': 'cry',
                'target': False,
                'text': 'cries in the corner'
            },
            'cmd_cuddle': {
                'type': 'cuddle',
                'target': True,
                'text': 'cuddles'
            },
            'cmd_kiss': {
                'type': 'kiss',
                'target': True,
                'text': 'kisses'
            },
            'cmd_lewd': {
                'type': 'lewd',
                'target': False,
                'text': 'is feeling lewd'
            },
            'cmd_nom': {
                'type': 'nom',
                'target': False,
                'text': 'is eating something. Seems delicious'
            },
            'cmd_nyan': {
                'type': 'nyan',
                'target': False,
                'text': 'says Nyaaaaa~~~'
            },
            'cmd_owo': {
                'type': 'owo',
                'target': False,
                'text': 'feels ...?'
            },
            'cmd_pat': {
                'type': 'pat',
                'target': True,
                'text': 'pats'
            },
            'cmd_pout': {
                'type': 'pout',
                'target': False,
                'text': 'is feeling bad'
            },
            'cmd_slap': {
                'type': 'slap',
                'target': True,
                'text': 'slaps'
            },
            'cmd_smug': {
                'type': 'smug',
                'target': False,
                'text': 'smugs'
            },
            'cmd_stare': {
                'type': 'stare',
                'target': True,
                'text': 'stares at'
            },
            'cmd_tickle': {
                'type': 'tickle',
                'target': True,
                'text': 'tickles'
            },
            'cmd_triggered': {
                'type': 'triggered',
                'target': False,
                'text': 'is triggered'
            },
            'cmd_lick': {
                'type': 'lick',
                'target': True,
                'text': 'licks'
            }
        }

        for cmd in pic_cmds:
            f = _pic_func(pic_cmds[cmd])
            setattr(self, cmd, f)

        if os.path.exists('audio_cache'):
            shutil.rmtree('audio_cache')

        os.mkdir('audio_cache')

        return super(MainClient, self).__init__()

    def load_config(self):
        try:
            with open('config/global.yaml') as f:
                self.config = yaml.load(f, Loader=yaml.CSafeLoader)
        except FileNotFoundError:
            with open('config/global_sample.yaml') as f:
                self.config = yaml.load(f, Loader=yaml.CSafeLoader)
        
        if 'YOUTUBE_APIKEY' in os.environ:
            self.youtube_apikey = os.environ['YOUTUBE_APIKEY']

    def on_ready(self):
        print('Logged on as %s' % (self.user))
        print('Set Prefix: %s' % self.prefix)
        print('Connected to:')
        for guild in self.guilds:
            print(' - {0.name} ({0.id})'.format(guild))

    async def on_message(self, message):
        if not message.author.bot:
            print('Message from {0.author}: {0.content}'.format(message))
            if message.content.startswith(self.prefix):
                m = message.content[1:]
                c = m.split(' ')[0]

                if hasattr(self, 'cmd_' + c):
                    cmd = getattr(self, 'cmd_' + c)

                    if ' ' in message.content:
                        has_args = True
                    else:
                        has_args = False

                    if not has_args:
                        try:
                            await cmd(message, None)
                        except TypeError:
                            await message.channel.send('```prolog\n{0}```'.format(dedent(cmd.__doc__)))
                    else:
                        try:
                            await cmd(message, *m[len(c) + 1:].split(' '))
                        except TypeError:
                            await message.channel.send('```prolog\n{0}```'.format(dedent(cmd.__doc__)))
