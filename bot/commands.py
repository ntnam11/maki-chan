import asyncio
import datetime
import io
import logging
import os
import random
import re
import shutil
import tempfile
import platform
import time
import traceback
import urllib
from textwrap import dedent
from threading import Timer

import aiohttp
import discord
import psutil
import requests
import yaml
from bs4 import BeautifulSoup
from PIL import Image

from .common import *
from .exceptions import *
from .games import Games
from .lovelive import LoveLive
from .misc import Misc
from .music import Music

logger = logging.getLogger('root.commands')

async def _get_pic(img_type):
	url = "https://rra.ram.moe/i/r?type=%s" % (img_type)
	network_timeout = False

	while not network_timeout:
		async with aiohttp.ClientSession() as session:
			async with session.get(url) as r:
				if r.status == 200:
					js = await r.json()
					link = js['path']
					url = "https://rra.ram.moe%s" % (link)
					break
				else:
					print('Error: %s' % r.status)
					network_timeout = True
					return {'error': True, 'message': 'HTTP Error %s. Please try again.' % r.status}

	return {'error': False, 'url': url}

def _pic_func(func_obj):
	if func_obj['target']:
		async def target_func(message, target, *args):
			'''
			Sends a pic
			Command group: Pics with target
			Usage: {command_prefix}[action] [mention / text]
			Example: {command_prefix}[action] / {command_prefix}[action] @_Kotori_
			'''
			url = await _get_pic(func_obj['type'])
			if url['error']:
				await message.channel.send(url['message'])
			else:
				if not target:
					target = 'himself'
				if len(message.mentions) > 0:
					target = message.mentions[0].name
				e = discord.Embed(title='{0} {1} {2}'.format(message.author.name, func_obj['text'], target))
				e.set_image(url=url['url'])
				await message.channel.send(embed=e)
				await delete_message(message)
		
		return target_func
	else:
		async def notarget_func(message, *args):
			'''
			Sends a pic
			Command group: Pics
			Usage: {command_prefix}[action]
			Example: {command_prefix}[action]
			'''
			url = await _get_pic(func_obj['type'])
			if url['error']:
				await message.channel.send(url['message'])
			else:
				e = discord.Embed(title='{0} {1}'.format(message.author.name, func_obj['text']))
				e.set_image(url=url['url'])
				await message.channel.send(embed=e)
				await delete_message(message)
		return notarget_func

class Commands(Music, Games, LoveLive, Misc):
	def __init__(self):
		return super(Commands, self).__init__()

	async def cmd_setprefix(self, message, prefix, *args, **kwargs):
		'''
		Set bot's prefix
		Command group: Special
		Usage: {command_prefix}setprefix [prefix]
		Example: {command_prefix}setprefix !
		'''
		self.prefix = prefix
		await message.channel.send('```Set prefix: {0}```'.format(prefix))
		print('Set prefix: %s' % (prefix))

	@owner_only
	async def cmd_setavatar(self, message, url):
		'''
		Set bot's avatar
		Command group: Special
		Usage: {command_prefix}setavatar [url/image attachment]
		Example: {command_prefix}setavatar https://c7.uihere.com/files/736/106/562/maki-nishikino-tsundere-japanese-idol-love-live-sunshine-manga-others.jpg
		'''
		if isinstance(url, str):
			async with aiohttp.ClientSession() as session:
				async with session.get(url) as r:
					if r.status == 404:
						await message.channel.send('Hm... URL not found. Try again')
					elif r.status == 200:
						fp = await r.read()
						await self.user.edit(avatar=fp)
		else:
			if len(message.attachments) > 0:
				a = message.attachments[0]
				fp = await message.attachments[0].read()
				await self.user.edit(avatar=fp)
			pass
		await message.channel.send('```uwu new avatar```')
		print('Set avatar: %s' % (url))
	
	async def cmd_avatar(self, message, *args):
		'''
		View bot's or someone's avatar
		Command group: Special
		Usage: {command_prefix}avatar [user]
		Example:
			{command_prefix}avatar
			{command_prefix}avatar @_Kotori_
		'''
		embed = discord.Embed()

		if len(args) > 0:
			if len(message.mentions) > 0:
				target = message.mentions[0]
				embed.set_image(url=target.avatar_url)
				await message.channel.send(f'{target.name}\'s avatar', embed=embed)
				return

		embed.set_image(url=self.user.avatar_url)
		await message.channel.send('Hi! This is my avatar :heart:', embed=embed)

	async def cmd_help(self, message, command, *args, **kwargs):
		'''
		Display help
		Command group: Special
		Usage: {command_prefix}help [command]
		Example: {command_prefix}help setprefix
		'''
		e = discord.Embed()
		
		if not command or command == '':
			groups = {}
			async with message.channel.typing():
				for attr in dir(self):
					if attr.startswith('cmd_'):
						help_info = dedent(getattr(self, attr).__doc__)
						group = re.findall('Command group: (.*)\n', help_info)[0]
						if group not in groups:
							groups[group] = []
						groups[group].append(attr[4:])
				e.title = 'Command list'
				for group in groups:
					e.add_field(name=group, value=', '.join(groups[group]), inline=False)
			await message.channel.send(f'```css\nType {self.prefix}help [command] to know more about a command```', embed=e)
		
		else:
			if 'cmd_' + command in dir(self):
				desc = dedent(getattr(self, 'cmd_' + command).__doc__)
				if '[action]' in desc:
					desc = desc.replace('[action]', command)

				_ = {
					'Description': desc[:desc.index('Command group')],
					'Command group': desc[desc.index('Command group'):desc.index('Usage')].replace('Command group:', ''),
					'Usage': desc[desc.index('Usage'):desc.index('Example')].replace('Usage:', '').replace('{command_prefix}', self.prefix),
					'Example': desc[desc.index('Example'):].replace('Example:', '').replace('{command_prefix}', self.prefix)
				}
				for k, v in _.items():
					e.add_field(name=k, value=v, inline=False)
				
				await message.channel.send('```css\nHelp for "%s"```' % command, embed=e)
			else:
				await message.channel.send('Command not found')
				return
	
	@owner_only
	async def cmd_shutdown(self, message, *args):
		'''
		Force a shutdown (´･ω･`)
		Command group: Owner only
		Usage: {command_prefix}shutdown
		Example: {command_prefix}shutdown
		'''
		if self.voice_client:
			if self.voice_client.is_connected():
				if self.voice_client.is_playing():
					self.voice_client.stop()
				await self.voice_client.disconnect()
		
		await message.channel.send(':wave:')
		raise SleepException

	async def cmd_flush(self, message, *args):
		'''
		Force a memory flush & clean all cache
		Command group: Special
		Usage: {command_prefix}flush
		Example: {command_prefix}flush
		'''
		if self.voice_client:
			if self.voice_client.is_connected():
				if self.voice_client.is_playing():
					self.voice_client.stop()
				await self.voice_client.disconnect()
		
		self.playing_cardgame = False
		self.playing_lyricgame = False
		self.playing_songgame = False
		self.playing_radio = False
		self.voice_client = None
		self.voice_channel = None
		self.music_queue = []
		self.current_song = None
		self.voice_text_channel = None
		self.force_stop_radio = False
		self.force_stop_music = False
		self.music_loop = False
		self.scouting = False
		self.radio_cache = []
		self.radio_requests = {}

		await message.channel.send('```css\nDone```')
		
	async def cmd_changelog(self, message, *args):
		'''
		Show most recent changelog
		Command group: Misc
		Usage: {command_prefix}flush
		Example: {command_prefix}flush
		'''
		str_result = 'md\n'

		with open('CHANGELOG.md') as f:
			content = f.readlines()

		_ = 0

		for line in content:
			if line != '\n':
				str_result += line
			else:
				if _ == 1:
					break
				_ += 1
				str_result += line

		str_result += '\n/* Full changelog: https://github.com/ntnam11/maki-chan/blob/master/CHANGELOG.md */'

		await message.channel.send('```' + str_result.replace('`', '') + '```')

	# @owner_only
	async def cmd_debug(self, message, command, *args):
		'''
		Debug mode (For experts only)
		Command group: Special
		Usage:
			{command_prefix}debug [command]
		Example:
			{command_prefix}debug self
		'''
		command = ' '.join([command, *args])
		forbidden = ['import', 'del', 'os', 'shutil', 'sys', 'open', 'eval', 'exec']
		for f in forbidden:
			if command.startswith(f):
				await message.channel.send('```python\nForbidden. Please try another command```')
				return

		try:
			scope = locals().copy()
			cmd_result = eval(command, scope)
		except Exception as e:
			cmd_result = repr(e)
		result = '```python\n%s```' % (cmd_result)
		await send_long_message(message.channel, result, prefix='```python\n', suffix='```')

	@owner_only
	async def cmd_message(self, message, uid, content, *args):
		'''
		Send a message to a user
		Command group: Owner only
		Usage:
			{command_prefix}message [uid] [content]
			- uid: User id
			- content: message to send
		Example:
			{command_prefix}message 309579216322691073 Hi!
		'''
		for guild in self.guilds:
			for member in guild.members:
				if member.id == int(uid):
					await member.send(content + ' '.join(args))
					return
		await message.channel.send('```User not found. Perhaps you don\'t share the same server with the user```')
	
	@owner_only
	async def cmd_listserver(self, message, *args):
		'''
		List joined server
		Command group: Owner only
		Usage:
			{command_prefix}listserver
		Example:
			{command_prefix}listserver
		'''
		result = ''
		for guild in self.guilds:
			result += f'{guild.id}: {guild.name}\n'
		await message.channel.send(f'```{result}```')

	@owner_only
	async def cmd_leaveserver(self, message, server_id, *args):
		'''
		Leave a server
		Command group: Owner only
		Usage:
			{command_prefix}leaveserver [server_id]
		Excample:
			{command_prefix}leaveserver 332012392104912758
		'''
		try:
			guild = self.get_guild(int(server_id))
			if guild is not None:
				await guild.leave()
				await message.channel.send('```css\nDone```')
				return
		except ValueError:
			await message.channel.send('```Invalid server ID```')
		await message.channel.send('```prolog\nI\'m not in that server (*´д｀*)```')

	@owner_only
	async def cmd_config(self, message, key, value, *args):
		'''
		Set bot's configuration
		Command group: Owner only
		Usage:
			{command_prefix}config [key] [value]
		Example:
			{command_prefix}config active_from 8
		'''
		if key == 'skip_status':
			if value in ['true', 'True', 't', 'T', 1, '1']:
				self.skip_status = True
			if value in ['false', 'False', 'f', 'F', 0, '0']:
				self.skip_status = False
			await message.channel.send(f'```css\nSkip changing status: {self.skip_status}```')
			return
		if key not in self.config:
			await message.channel.send('```fix\nConfig key not found```')
		else:
			t = type(self.config[key])
			try:
				self.config[key] = t(value)
			except ValueError:
				self.config[key] = value

			try:
				setattr(self, key, t(value))
			except ValueError:
				setattr(self, key, value)

			with open('config/global.yaml', mode='w+') as f:
				yaml.dump(self.config, f, Dumper=yaml.CSafeDumper)
			
		await message.channel.send('```css\nDone```')

	async def cmd_apistatus(self, message, *args):
		'''
		Show server status info
		Command group: Special
		Usage:
			{command_prefix}status
		Example:
			{command_prefix}status
		'''
		check = {
			'cardgame': {
				'url': 'https://schoolido.lu/api/cards/315/',
				'status': 'Timed out'
			},
			'songgame': {
				'url': 'https://love-live.fandom.com/wiki/Bokutachi_wa_Hitotsu_no_Hikari',
				'status': 'Timed out'
			},
			'cardgame_as': {
				'url': 'https://idol.st/allstars/cards/random/',
				'status': 'Timed out'
			},
		}

		for k, v in check.items():
			try:
				r = requests.get(v['url'])
			except requests.exceptions.ReadTimeout:
				pass
			else:
				if r.status_code == 200:
					v['status'] = 'OK'
				elif r.status_code == 404:
					v['status'] = 'Not found'
				elif str(r.status_code).startswith('5'):
					v['status'] = 'Server Error'

		result = {
			'Cardgame': check['cardgame']['status'],
			'Cardgame - All stars': check['cardgame_as']['status'],
			'Songgame': check['songgame']['status'],
			'Lyricgame': check['songgame']['status'],
			'Randomcard': check['cardgame']['status'],
			'Cardinfo': check['cardgame']['status'],
			'Idolinfo': check['cardgame']['status'],
			'Scout': check['cardgame']['status']
		}
		
		strresult = ''
		for k, v in result.items():
			strresult += f'- {k}: {v}\n'

		await message.channel.send(f'```prolog\nCurrent status:\n{strresult}```')
	
	@owner_only
	async def cmd_status(self, message, status_text, *args):
		'''
		Change bot's status text
		Command group: Owner only
		Usage:
			{command_prefix}status [status_text]
		Example:
			{command_prefix}status Singing a song~
		'''
		game = discord.Game(' '.join([status_text, *args]))
		await self.change_presence(activity=game)

	async def cmd_info(self, message, *args):
		'''
		Show bot's debug information
		Command group: Owner only
		Usage:
			{command_prefix}info
		Example:
			{command_prefix}info
		'''
		psutil.cpu_percent(interval=None)
		embed = discord.Embed()

		cpu_time = str(datetime.timedelta(seconds=time.time() - psutil.boot_time()))
		mem = psutil.virtual_memory()
		await asyncio.sleep(1)
		cpu_percent = psutil.cpu_percent(interval=None)

		version = discord.version_info
		version = f'v{version.major}.{version.minor}.{version.micro} ({version.releaselevel})'

		embed.add_field(name='Platform', value=platform.platform())
		embed.add_field(name='Python', value=f'v{platform.python_version()}')
		embed.add_field(name='Discord', value=version)
		embed.add_field(name='Uptime', value=cpu_time, inline=False)
		embed.add_field(name='%CPU', value=cpu_percent)
		embed.add_field(name='RAM', value=f'{mem.used >> 20}/{mem.total >> 20}')
		embed.add_field(name='%RAM', value=mem.percent)
		embed.add_field(name='Guilds', value=len(self.guilds))
		embed.add_field(name='Users', value=len(self.users))
		embed.add_field(name='Latency', value=f'{round(self.latency * 100)/100}s')

		await message.channel.send(embed=embed)
