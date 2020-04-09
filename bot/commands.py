import re
import aiohttp
import logging
import time
import tempfile
import asyncio
import random
import urllib
import io
import shutil
import traceback
import os
import requests
import yaml

from threading import Timer
from textwrap import dedent

import discord
from PIL import Image
from bs4 import BeautifulSoup
from .player import MusicPlayer
from .games import Games, SIF_IDOL_NAMES, SIF_NAME_LIST, MAX_SIF_CARDS
from .exceptions import *
from .common import *

logger = logging.getLogger('Command')

SIF_COLOR_LIST = {
	'Ayase Eli': 0x36B3DD, 'Hoshizora Rin': 0xF1C51F, 'Koizumi Hanayo': 0x54AB48,
	'Kousaka Honoka': 0xE2732D, 'Minami Kotori': 0x8C9395, 'Nishikino Maki': 0xCC3554,
	'Sonoda Umi': 0x1660A5, 'Toujou Nozomi': 0x744791, 'Yazawa Nico': 0xD54E8D,
	'Takami Chika': 0xF0A20B, 'Sakurauchi Riko': 0xE9A9E8, 'Watanabe You': 0x49B9F9,
	'Tsushima Yoshiko': 0x898989, 'Kurosawa Ruby': 0xFB75E4, 'Kunikida Hanamaru': 0xE6D617,
	'Ohara Mari': 0xAE58EB, 'Kurosawa Dia': 0xF23B4C, 'Matsuura Kanan': 0x13E8AE,
	'Kira Tsubasa': 0xFFFFFF, 'Toudou Erena': 0xFFFFFF, 'Yuuki Anju': 0xFFFFFF,
	'Miyashita Ai': 0xFDA566, 'Yuki Setsuna': 0xFD767A, 'Emma Verde': 0xA6E37B,
	'Asaka Karin': 0x96B1E8, 'Uehara Ayumu': 0xE792A9, 'Osaka Shizuku': 0xAEDCF4,
	'Tennoji Rina': 0xAEABAE, 'Konoe Kanata': 0xD299DE, 'Nakasu Kasumi': 0xF2EB90,
	'Alpaca': 0x8C9395, 'Shiitake': 0xE9A9E8, 'Uchicchi': 0x49B9F9,
	"Chika's Mother": 0xF0A20B, "Honoka's Mother": 0xE2732D, "Kotori's Mother": 0x8C9395, "Maki's Mother": 0xCC3554, "Nico's Mother": 0xD54E8D,
	'Yazawa Cocoa': 0xD54E8D, 'Yazawa Cocoro': 0xD54E8D, 'Yazawa Cotarou': 0xD54E8D,
}

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
			Example: ~[action] / ~[action] @_Kotori_
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
			Example: ~[action]
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

class Commands(MusicPlayer, Games):
	def __init__(self):
		return super(Commands, self).__init__()

	async def cmd_setprefix(self, message, prefix, *args, **kwargs):
		'''
		Set bot's prefix
		Command group: Special
		Usage: {command_prefix}setprefix [prefix]
		Example: ~setprefix !
		'''
		self.prefix = prefix
		await message.channel.send('```Set prefix: {0}```'.format(prefix))
		print('Set prefix: %s' % (prefix))

	@owner_only
	async def cmd_setavatar(self, message, url):
		'''
		Set bot's avatar
		Command group: Special
		Usage {command_prefix}setavatar [url/image attachment]
		Example: ~setavatar https://c7.uihere.com/files/736/106/562/maki-nishikino-tsundere-japanese-idol-love-live-sunshine-manga-others.jpg
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

	async def cmd_help(self, message, command, *args, **kwargs):
		'''
		Display help
		Command group: Special
		Usage: {command_prefix}help [command]
		Example: ~help / ~help setprefix
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
			await message.channel.send(embed=e)
		
		else:
			if 'cmd_' + command in dir(self):
				desc = dedent(getattr(self, 'cmd_' + command).__doc__)
				if '[action]' in desc:
					desc = desc.replace('[action]', command)

				_ = {
					'Description': desc[:desc.index('Command group')],
					'Command group': desc[desc.index('Command group'):desc.index('Usage')].replace('Command group:', ''),
					'Usage': desc[desc.index('Usage'):desc.index('Example')].replace('Usage:', ''),
					'Example': desc[desc.index('Example'):].replace('Example:', '')
				}
				for k, v in _.items():
					e.add_field(name=k, value=v, inline=False)
				
				await message.channel.send('```css\nHelp for "%s"```' % command, embed=e)
			else:
				await message.channel.send('Command not found')
				return
	
	async def cmd_say(self, message, *args):
		'''
		Make the bot say something
		Command group: Misc
		Usage: {command_prefix}say [text]
		Example: ~say Hello!
		'''
		await message.channel.send(' '.join(args))
		await delete_message(message)
	
	async def cmd_bigtext(self, message, *args):
		"""
		Display a BIGTEXT :D
		Command group: Misc
		Usage: {command_prefix}bigtext [text]
		Example: ~bigtext woohoo
		"""
		result = ""
		
		for word in args:
			for s in word:
				if s != ' ':
					result += ":regional_indicator_%s:" % s
			result += " "

		await message.channel.send(result)
		await delete_message(message)

	async def cmd_lenny(self, message, *args):
		'''
		Sends a ( ͡° ͜ʖ ͡°)
		Command group: Pics
		Usage: {command_prefix}lenny
		Example: ~lenny
		'''
		await message.channel.send('( ͡° ͜ʖ ͡°)')
		await delete_message(message)

	async def cmd_cat(self, message, *args):
		'''
		Sends a random cat from random.cat
		Command group: Misc
		Usage: {command_prefix}cat
		Example: ~cat
		'''
		url = "https://aws.random.cat/meow"
		network_timeout = False

		while not network_timeout:
			async with aiohttp.ClientSession() as session:
				async with session.get(url) as r:
					if r.status == 200:
						js = await r.json()
						url = js['file']
						# url = "https://rra.ram.moe%s" % (link)
						break
					else:
						print('Error: %s' % r.status)
						network_timeout = True
						return {'error': True, 'message': 'HTTP Error %s. Please try again.' % r.status}

		await message.channel.send(url)
		# return {'error': False, 'url': url}

	async def cmd_join(self, message, *args):
		'''
		Join a voice channel
		Command group: Music
		Usage: {command_prefix}join
		Example: ~join
		'''
		if self.voice_client:
			if self.voice_client.is_playing():
				await message.channel.send('```prolog\nSorry. I\'m busy playing some music now :(```')
				return {'error': True}

		try:
			self.voice_channel = message.author.voice.channel
		except AttributeError:
			await message.channel.send('```css\nPlease join a voice channel first :D```')
			return {'error': True}
			
		try:
			self.voice_client = await self.voice_channel.connect()
			if not self.voice_client:
				self.voice_client = self.voice_clients[0]
		except asyncio.TimeoutError:
			await message.channel.send('```css\nCould not connect to the voice channel in time```')
			return {'error': True}
		except discord.ClientException:
			await message.channel.send('```css\nAlready connected to voice channel```')
			return {'error': True}
		except discord.opus.OpusNotLoaded:
			try:
				from opus_loader import load_opus_lib
				load_opus_lib()
			except RuntimeError:
				await message.channel.send('```css\nError loading opus lib. Cannot join voice channel```')
				return {'error': True}

		await message.channel.send('```css\nConnected to "%s"```' % self.voice_channel.name)
		return {'error': False}
	
	async def cmd_leave(self, message, *args):
		'''
		Leave a voice channel
		Command group: Music
		Usage: {command_prefix}leave
		Example: ~leave
		'''
		if self.playing_radio:
			self.force_stop_radio = True
		if not self.voice_client and not self.voice_channel:
			# await message.channel.send('```prolog\nHm... I haven\'t joined any voice channel```')
			return
		if self.voice_client.is_playing():
			self.voice_client.stop()
		await self.voice_client.disconnect()
		if message:
			await message.channel.send('```prolog\nLeft "%s"```' % self.voice_channel.name)
		self.voice_channel = None
		self.voice_client = None
		self.playing_radio = False
		self.force_stop_radio = False

	async def cmd_play(self, message, query, *args):
		'''
		(Search and) Queue a youtube video url
		Command group: Music
		Usage:
			{command_prefix}play [query]
			- Search a video and queue the first result
			
			{command_prefix}play [youtube_url]
			- Queue the youtube_url

		Example:
			~play snow halation
			~play https://www.youtube.com/watch?v=g1p5eNOsl7I
		'''
		if not self.youtube_apikey or self.youtube_apikey == '':
			await message.channel.send('```css\nYoutube API key not found. Please set one in global.yaml or environment variable```')
			return

		if not self.voice_channel:
			await self.cmd_join(message)

		if len(self.music_queue) >= 50:
			await message.channel.send('```css\nCannot add song due to maximum queue length reached```')
			return
		
		self.voice_text_channel = message.channel

		async with message.channel.typing():
			await self._process_query(*[query, *args])

	async def cmd_search(self, message, query, *args):
		'''
		Search a video on youtube, up to 10 results
		Command group: Music
		Usage: {command_prefix}search [query]
		Example: ~search snow halation
		'''
		if not self.youtube_apikey or self.youtube_apikey == '':
			await message.channel.send('```fix\nYoutube API key not found. Please set one in global.yaml or environment variable```')
			return

		if len(self.music_queue) >= 50:
			await message.channel.send('```fix\nCannot add song due to maximum queue length reached```')
			return

		async with message.channel.typing():
			r = await self._youtube_search(' '.join([query, *args]))

			str_result = '```css\n'

			if r['error']:
				await message.channel.send('```fix\n%s```' % r['message'])
			else:
				for i, result in enumerate(r['result']):
					str_result += '%s. %s\n' % (i, result['title'])
			
			str_result += 'c. Cancel```'

			await message.channel.send(str_result)
				
		def _cond(m):
			return m.channel == message.channel

		start = int(time.time())
		checktimeout = False
		while True:
			if (int(time.time()) - start) >= 30:
				checktimeout = True

			try:
				response_message = await self.wait_for('message', check=_cond, timeout=30)
			except asyncio.TimeoutError:
				response_message = None

			if (checktimeout == True) or (not response_message):
				await message.channel.send('```fix\nTimeout. Request aborted```')
				return

			resp = response_message.content.lower()

			if (resp == 'c'):
				await message.channel.send('```css\nOkay. Nevermind```')
				return

			if not resp.isdigit() or int(resp) not in range(0, len(r['result'])):
				await message.channel.send('```fix\nPlease type the correct number```')
			
			else:
				break

		self.voice_text_channel = message.channel

		if not self.voice_channel:
			await self.cmd_join(message)

		async with message.channel.typing():
			await self._process_query('https://www.youtube.com/watch?v=' + r['result'][int(resp)]['id'], title=r['result'][int(resp)]['title'])

	async def cmd_np(self, message, *args):
		'''
		Show what's being played in voice channel
		Command group: Music
		Usage: {command_prefix}np
		Example: ~np
		'''
		if self.playing_radio:
			await message.channel.send('```fix\nNow playing non-stop Love Live!! songs```')
			return

		if self.current_song:
			await message.channel.send('```fix\nNow playing: %s```\n%s' % (self.current_song.title, self.current_song.url))
		else:
			await message.channel.send('```fix\nNothing is being played at the moment. Wanna add some?```')

	async def cmd_skip(self, message, *args):
		'''
		Skip current playing song in voice channel
		Command group: Music
		Usage: {command_prefix}skip
		Example: ~skip
		'''
		if self.playing_radio:
			if self.voice_client:
				if self.voice_client.is_playing():
					self.voice_client.stop()
			# await self.cmd_llradio(message)
			return
		if self.current_song:
			self.voice_client.stop()
			await message.channel.send('```fix\nSkipped %s```' % self.current_song.title)
			await self._process_queue()
		else:
			await message.channel.send('```fix\nNothing to skip at the moment```')

	async def cmd_queue(self, message, *args):
		'''
		Show music queue
		Command group: Music
		Usage: {command_prefix}queue
		Example: ~queue
		'''
		if len(self.music_queue) == 0:
			await message.channel.send('```css\nNo song in queue. Wanna add some?```')
			return

		str_result = '```css\n'

		for i, result in enumerate(self.music_queue):
			str_result += '%s. %s\n' % (i + 1, result.title)
		
		str_result += '```'

		await message.channel.send(str_result)

	@owner_only
	async def cmd_shutdown(self, message, *args):
		'''
		Force a shutdown :D
		Command group: Owner only
		Usage: {command_prefix}shutdown
		Example: ~shutdown
		'''
		if self.voice_client:
			if self.voice_client.is_connected():
				if self.voice_client.is_playing():
					self.voice_client.stop()
				await self.voice_client.disconnect()
		
		await message.channel.send(':wave:')
		exit()

	async def cmd_flush(self, message, *args):
		'''
		Force a memory flush & clean all cache
		Command group: Special
		Usage: {command_prefix}flush
		Example: ~flush
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
		self.loop = False

		await message.channel.send('```css\nDone```')
		
	async def cmd_changelog(self, message, *args):
		'''
		Show most recent changelog
		Command group: Misc
		Usage: {command_prefix}flush
		Example: ~flush
		'''
		str_result = '```md\n'

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

		str_result += '\n/* Full changelog: https://github.com/ntnam11/maki-chan/blob/master/CHANGELOG.md */```'

		await message.channel.send(str_result)

	async def cmd_cardinfo(self, message, card_id, *args, internal=False):
		'''
		Show info of a LLSIF card by id (idolized if defined)
		Command group: LLSIF
		Usage: {command_prefix}cardinfo card_id [idlz / idolized]
		Example:
			~cardinfo 2145
			~cardinfo 2145 idlz
		'''
		promo = ''
		getinfo = 'card_image'
		card_id = str(card_id)

		if not card_id.isdigit():
			await message.channel.send('```prolog\nPlease type card id properly```')
			return
		else:
			if args:
				if args[0].lower() in ['idlz', 'idolized']:
					getinfo = 'card_idolized_image'

		async with message.channel.typing():
			url = 'http://schoolido.lu/api/cards/%s/' % (card_id)

			async with aiohttp.ClientSession() as session:
				async with session.get(url) as r:
					if r.status == 200:
						js = await r.json()
						img = 'http:%s' % (js[getinfo])
						card_name = js['idol']['name']
						collection = js['translated_collection']
						release_date = js['release_date']
						is_promo = js['is_promo']
						attribute = js['attribute']
						ranking_attribute = js['ranking_attribute']
						if img == "http:None":
							if not internal:
								await message.channel.send('This card does not have unidolized version. Here\'s the idolized.')
							img = 'http:%s' % (js['card_idolized_image'])
						if is_promo == 'True':
							promo = 'Promo Card\n'
						else:
							promo = ''

						await message.channel.send(
							f'{img}\n```prolog\nCard No. {card_id}\nName: {card_name}\nCollection: {collection}\n' +
							f'Released date: {release_date}\n{promo}#{ranking_attribute} best {attribute} card```\n'
						)
						return 1
					else:
						if not internal:
							await message.channel.send('```prolog\nNetwork timed out or card not found.```')
						return 0

	async def cmd_randomcard(self, message, *args):
		'''
		Show info of a random LLSIF card by idol / rarity
		Command group: LLSIF
		Usage:
			{command_prefix}randomcard [idol] [rarity]
			- idol: 
				maki, rin, hanayo, kotori, honoka, umi, eli, nozomi, nico,
				ruby, hanamaru, yoshiko, yohane, you, chika, riko, mari, kanan, dia,
				ayumu, ai, setsuna, kanata, karin, emma, rina, shizuku, kasumi,
				and some support characters
			- rarity: R, SR, SSR, UR
		Example:
			~randomcard
			~randomcard kotori
			~randomcard ur
			~randomcard kotori ur
		'''
		if not args:
			found = False
			while not found:
				random_id = random.randint(1, MAX_SIF_CARDS)
				r = await self.cmd_cardinfo(message, random_id, internal=True)
				if r:
					return

		url = 'http://schoolido.lu/api/cardids/?'

		args = list(args)

		while args:
			query = args.pop(0)
			if query is not None:
				query = query.lower()
				if query in SIF_NAME_LIST:
					url += 'name=%s&' % SIF_IDOL_NAMES[query]
					logger.info('Set url: %s' % url)
				
				if query in ['r', 'sr', 'ssr', 'ur']:
					url += 'rarity=%s&' % query
					logger.info('Set url: %s' % url)
			
		async with message.channel.typing():
			async with aiohttp.ClientSession() as session:
				async with session.get(url) as r:
					if r.status == 200:
						js = await r.json()
						card_num = random.choice(js)
						logger.info('Random card: %s' % card_num)
						await self.cmd_cardinfo(message, card_num)
						return
					else:
						logger.info('Error: %s' % r.status)
						await message.channel.send('```prolog\nHTTP Error %s. Please try again later.```' % r.status)
						return
	
	async def cmd_idolinfo(self, message, query, *args):
		'''
		Show info of a Love Live!! Idol
		Command group: LLSIF
		Usage:
			{command_prefix}idolinfo [name]
			- name:
				maki, rin, hanayo, kotori, honoka, umi, eli, nozomi, nico,
				ruby, hanamaru, yoshiko, yohane, you, chika, riko, mari, kanan, dia,
				ayumu, ai, setsuna, kanata, karin, emma, rina, shizuku, kasumi
		Example:
			~idolinfo kotori
		'''
		logger.info("Searched for %s" % (query))

		if query not in SIF_NAME_LIST:
			await message.channel.send('```prolog\nIdol not found.```')
			return

		idol = SIF_IDOL_NAMES[query]

		url = 'http://schoolido.lu/api/idols/%s/' % (idol)
		logger.info("Getting info from %s" % (url))

		async with aiohttp.ClientSession() as session:
			async with session.get(url) as r:
				if r.status == 200:
					js = await r.json()

					name = js['name']
					jpname = js['japanese_name']
					age = js['age']
					school = js['school']
					birthday = js['birthday']
					astrological_sign = js['astrological_sign']
					blood = js['blood']
					height = js['height']
					measurements = js['measurements']
					favorite_food = js['favorite_food']
					least_favorite_food = js['least_favorite_food']
					hobbies = js['hobbies']
					attribute = js['attribute']
					year = js['year']
					main_unit = js['main_unit']
					sub_unit = js['sub_unit']

					try:
						cv_name = js['cv']['name']
					except:
						cv_name = js['cv']
					try:
						cv_nickname = js['cv']['nickname']
					except:
						cv_nickname = js['cv']

					summary = js['summary']
					chibi = js['chibi_small']

				else:
					await message.channel.send('```prolog\nError occurs. Please try again later.```')

		e = discord.Embed(title="Idol information", type="rich", color=SIF_COLOR_LIST[name])

		e.set_thumbnail(url="%s" % chibi)

		e.add_field(name="Name", value=name, inline=True)
		e.add_field(name="Japanese", value=jpname, inline=True)
		e.add_field(name="Age", value=age, inline=True)

		e.add_field(name="Birthday", value=birthday, inline=True)
		e.add_field(name="Sign", value=astrological_sign, inline=True)
		e.add_field(name="Year", value=year, inline=True)
		e.add_field(name="School", value=school, inline=True)

		e.add_field(name="Blood type", value=blood, inline=True)
		e.add_field(name="Height", value=height, inline=True)
		e.add_field(name="Measurements", value=measurements, inline=True)

		e.add_field(name="Favourite food", value=favorite_food, inline=True)
		e.add_field(name="Dislike food", value=least_favorite_food, inline=True)
		
		e.add_field(name="Hobbies", value=hobbies, inline=True)
		e.add_field(name="Main unit", value=main_unit, inline=True)
		e.add_field(name="Sub unit", value=sub_unit, inline=True)

		e.add_field(name="Summary", value=summary, inline=False)

		e.add_field(name="CV", value=cv_name, inline=True)
		e.add_field(name="Nickname", value=cv_nickname, inline=True)

		await message.channel.send('```css\nYou searched for "%s"\n```' % (query), embed=e)

	# @owner_only
	async def cmd_debug(self, message, *args):
		'''
		Debug mode (For experts only)
		Command group: Special
		Usage:
			{command_prefix}debug [command]
		Example:
			~debug self
		'''
		command = ' '.join(args)
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
		await message.channel.send(result)

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
			~message 309579216322691073 Hi!
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
			~listserver
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
			~leaveserver 332012392104912758
		'''
		try:
			guild = self.get_guild(int(server_id))
			if guild is not None:
				await guild.leave()
				await message.channel.send('```css\nDone```')
				return
		except ValueError:
			await message.channel.send('```Invalid server ID```')
		await message.channel.send('```prolog\nI\'m not in that server :(```')

	async def cmd_llradio(self, message, *args):
		'''
		Play a random Love Live!! song (including Sunshine, Nijigasaki & Saint Snow)
		If you want another Love Live! Radio instance, consider adding another me: https://discordapp.com/api/oauth2/authorize?client_id=697328604186411018&permissions=70569024&scope=bot
		Command group: Music
		Usage:
			{command_prefix}llradio
		Example:
			~llradio
		'''
		song_cache = os.path.join('game_cache', 'songs')
		song_list = os.path.join('game_cache', 'song_list')
		if not os.path.exists(song_list):
			songs_available = self._create_song_list()
		else:
			with open(song_list, mode='r') as f:
				songs_available = f.readlines()
		
		self.playing_radio = True

		if self.force_stop_radio:
			return

		if not self.voice_client:
			r = await self.cmd_join(message)
			if r['error']:
				return

		self.check_sleep(message)

		while True:
			song_url = random.choice(songs_available)
			r = requests.get(song_url.strip())
			soup =  BeautifulSoup(r.content, 'html5lib')

			song_name = soup.find('h1', {'class': 'page-header__title'}).text.strip()
			song_files = soup.find_all('div', {'class': 'ogg_player'})
			song_file = random.choice(song_files)

			for p in song_file.parents:
				if p.name == 'td':
					td = p
					break

			t = None

			for p in song_file.parents:
				if 'class' in p.attrs:
					if 'tabbertab' in p.attrs['class']:
						t = p
						break
				if 'id' in p.attrs:
					if p.attrs['id'] == 'mw-content-text':
						break

			if t is None:
				break

			if t.attrs['title'].lower() != 'radio drama':
					break

		song_length = td.previous_sibling
		song_name = song_length.previous_sibling.text.strip()

		song_onclick = song_file.find('button').attrs['onclick']
		song_url = re.search('"videoUrl":"(.*?)"', song_onclick)[1]

		song_r = requests.get(song_url)
		song_data = song_r.content
		with open(os.path.join('game_cache', 'radio.ogg'), mode='wb+') as f:
			f.write(song_data)

		source = discord.FFmpegPCMAudio(os.path.join(os.getcwd(), 'game_cache', 'radio.ogg'), executable='ffmpeg')

		md = random.choice(['fix', 'css', 'prolog', 'autohotkey', 'bash', 'coffeescript', 'md', 'ml', 'cs', 'diff', 'tex'])

		if md in ['diff']:
			prefix = '!'
		elif md in ['tex']:
			prefix = '$'
		else:
			prefix = '#'

		await message.channel.send(f'```{md}\n{prefix} Now playing: {song_name}```')

		self.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.cmd_llradio(message), self.loop))

	async def cmd_stop(self, message, *args):
		'''
		Force stop Love Live!! radio
		Command group: Music
		Usage: {command_prefix}stop
		Example: ~stop
		'''
		if self.playing_radio:
			self.force_stop_radio = True

		if self.voice_client:
			if self.voice_client.is_playing():
				self.voice_client.stop()

		await message.channel.send('```css\nDone```')

		self.force_stop_radio = False

	async def cmd_loop(self, message, *args):
		'''
		Loop a song
		Command group: Music
		Usage: {command_prefix}loop
		Example: ~loop
		'''
		if self.playing_radio:
			await message.channel.send('```fix\nWell, u can\'t loop a radio bruh :|```')
			return
		
		if not self.voice_client:
			await message.channel.send('```fix\nNothing to loop at the moment```')

		self.loop = not self.loop

		if self.loop:
			await message.channel.send('```prolog\nLoop: on```')
		else:
			await message.channel.send('```prolog\nLoop: off```')

	async def cmd_choose(self, message, choice, *args):
		'''
		Help u to choose something lmao
		Don't blame me if something goes wrong :|
		Command group: Misc
		Usage: {command_prefix}choose [option 1], [option 2],...
		Example: ~choose friend, like, love
		'''
		choices = [choice]

		if args is not None:
			text = ' '.join(args)
			choices.extend(text.split(', '))
		
		result = random.choice(choices)
			
		await message.channel.send(f'Well, I choose **{result}**!')

	@owner_only
	async def cmd_config(self, message, key, value, *args):
		'''
		Set bot's configuration
		Command group: Owner only
		Usage:
			{command_prefix}config [key] [value]
		Example:
			~config active_from 8
		'''
		if key not in self.config:
			await message.channel.send('```fix\nConfig key not found```')
		else:
			t = type(self.config[key])
			try:
				self.config[key] = t(value)
			except ValueError:
				self.config[key] = value

			with open('config/global.yaml', mode='w+') as f:
				yaml.dump(self.config, f, Dumper=yaml.CSafeDumper)
			
		await message.channel.send('```css\nDone```')

		self.load_config()