import asyncio
import difflib
import io
import logging
import os
import random
import shutil
import tempfile
import time
import urllib.request
import requests
import re

import subprocess

import aiohttp
import discord
import yaml
from PIL import Image
from bs4 import BeautifulSoup

from .exceptions import *

MAX_SIF_CARDS = 5000

SIF_IDOL_NAMES = {
	'eli': 'Ayase Eli', 'rin': 'Hoshizora Rin', 'umi': 'Sonoda Umi', 'hanayo': 'Koizumi Hanayo',
	'honoka': 'Kousaka Honoka', 'kotori': 'Minami Kotori', 'maki': 'Nishikino Maki', 'nozomi': 'Toujou Nozomi', 'nico': 'Yazawa Nico',
	'chika': 'Takami Chika', 'riko': 'Sakurauchi Riko', 'you': 'Watanabe You', 'yoshiko': 'Tsushima Yoshiko', 'yohane': 'Tsushima Yoshiko',
	'ruby': 'Kurosawa Ruby', 'hanamaru': 'Kunikida Hanamaru', 'mari': 'Ohara Mari', 'dia': 'Kurosawa Dia', 'kanan': 'Matsuura Kanan',
	'alpaca': 'Alpaca', 'shiitake': 'Shiitake', 'uchicchi': 'Uchicchi',
	"chika's mother": "Chika's mother", "honoka's mother": "Honoka's mother", "kotori's mother": "Kotori's mother", "maki's mother": "Maki's mother", "nico's mother": "Nico's mother",
	'cocoa': 'Yazawa Cocoa', 'cocoro': 'Yazawa Cocoro', 'cotarou': 'Yazawa Cotarou',
	'ayumu': 'Uehara Ayumu', 'setsuna': 'Yuki Setsuna', 'shizuku': 'Osaka Shizuku',
	'karin': 'Asaka Karin', 'kasumi': 'Nakasu Kasumi', 'ai': 'Miyashita Ai',
	'rina': 'Tennoji Rina', 'kanata': 'Konoe Kanata', 'emma': 'Emma Verde',
}
SIF_NAME_LIST = [
	'eli', 'rin', 'hanayo', 'honoka', 'kotori', 'maki', 'umi', 'nozomi', 'nico',
	'chika', 'riko', 'you', 'yoshiko', 'ruby', 'hanamaru', 'mari', 'dia', 'kanan', 'yohane',
	'alpaca', 'shiitake', 'uchicchi',
	"chika's mother", "honoka's mother", "kotori's mother", "maki's mother", "nico's mother",
	'cocoa', 'cocoro', 'cotarou',
	'ayumu', 'ai', 'setsuna', 'kanata', 'karin', 'emma', 'rina', 'shizuku', 'kasumi',
]

logger = logging.getLogger('Games')

def normalize_text(s):
	s = s.lower()
	result = ''
	for c in s:
		if ord(c) in range(97, 123) or c == ' ':
			result += c
	return result

class _Song:
	def __init__(self, url):
		self.text = url
		self.attrs = {
			'href': url
		}

class Games:
	def __init__(self):
		pass

	def _create_song_list(self):
		resource_url = 'https://love-live.fandom.com/wiki/Song_Centers'
		r = requests.get(resource_url)

		soup = BeautifulSoup(r.content, 'html5lib')
		
		tables = soup.find_all('table', {'class': 'article-table'})		
		songs_available = []
		for table in tables:
			songs = table.find_all('a', {'class': None})
			song_urls = []

			for song in songs:
				song_urls.append('https://love-live.fandom.com' + song.attrs['href'])
			
			songs_available.extend(song_urls)

		with open(os.path.join('game_cache', 'song_additional')) as f:
			content = f.readlines()

		for line in content:
			songs_available.append(line.strip())
		
		with open(os.path.join('game_cache', 'song_list'), mode='w+') as f:
			f.write('\n'.join(songs_available))

		return songs_available

	async def cmd_cardgame(self, message, card_num, *args):
		"""
		Play LLSIF card guessing game
		If the bot stucks, try {command_prefix}flush to clear its cache
		Command group: Games
		Usage:
			{command_prefix}cardgame card_num [diff] [custom_dimension]
			- card_num: Number of rounds to play
			- diff:
				+ easy/e: image size 300x300
				+ normal/n: image size 200 x 200
				+ hard/h: image size 150 x 150
				+ extreme/ex: image size 100 x 100
				+ custom/c: image size {custom_dimension} x {custom_dimension} 
			- custom_dimension: an integer between 10 - 400
			Normal diff by default

			stop to stop the game (for who called the game :D)

			Just type the answer without prefix :D
			
			Idol names including: 
				maki, rin, hanayo, kotori, honoka, umi, eli, nozomi, nico,
				ruby, hanamaru, yoshiko, yohane, you, chika, riko, mari, kanan, dia,
				ayumu, ai, setsuna, kanata, karin, emma, rina, shizuku, kasumi,
				and some support characters

			You must answer in 15 seconds :D
		Example:
			~cardgame 10 ex
			~cardgame 1
		"""
		try:
			if self.playing_cardgame:
				await message.channel.send("The game is currently being played. Enjoy!")
				return
		except AttributeError:
			self.playing_cardgame = True

		diff_size = {
			'easy': 300,
			'normal': 200,
			'hard': 150,
			'extreme': 100,
			'e': 300,
			'n': 200,
			'h': 150,
			'ex': 100
		}
		try:
			card_num = int(card_num)
			if card_num <= 0:
				raise ValueError
		except ValueError:
			await message.channel.send("Please type number of rounds correctly")
			self.playing_cardgame = False
			return

		def _cond(m):
			return m.channel == message.channel

		if card_num > 50:
			checktimeout = False
			checkproceed = False
			start = int(time.time())
			await message.channel.send("You really wanna play %s rounds? .-. Hm... Type `y` to proceed in 10 seconds, or `n` to quit" % card_num)

			while True:
				if (int(time.time() - start) >= 5):
					checktimeout = True
				try:
					response_message = await self.wait_for('message', check=_cond, timeout=10)
				except asyncio.TimeoutError:
					checktimeout = True
				else:
					if response_message.content == 'y':
						checktimeout = True
						checkproceed = True
					elif response_message.content == 'n':
						checktimeout = True

				if checktimeout:
					break
			
			if not checkproceed:
				await message.channel.send("Next time choose a smaller number of rounds :D")
				self.playing_cardgame = False
				return

		if not args:
			diff = 'normal'
		else:
			diff = args[0]
			if diff in diff_size:
				pass
			elif diff == 'custom' or diff == 'c':
				if not args:
					await message.channel.send("Please add a width (height) for custom difficulty. E.g. `custom 50`")
					self.playing_cardgame = False
					return

				try:
					dim = int(args[1])
				except ValueError:
					await message.channel.send("Please type custom width (height) correctly (10 - 500)")
					self.playing_cardgame = False
					return

				if dim < 10 or dim > 400:
					await message.channel.send("Please type custom width (height) correctly (10 - 500)")
					self.playing_cardgame = False
					return
				diff_size[diff] = dim
			else:
				await message.channel.send("Diff %s not found .-." % diff)
				self.playing_cardgame = False
				return		   

		user1st = message.author
		userinfo = {user1st.display_name: 0}
		struserlist = ""
		strresult = ""
		
		await message.channel.send("Game starts in 5 seconds. Be ready!")
		checkstart = False
		checktimeout = False
		start = int(time.time())
		logger.info("Game called at %s" % (start))

		self.playing_cardgame = True
		
		while True:
			if (int(time.time()) - start >= 5):
				checkstart = True
			try:
				response_message = await self.wait_for('message', check=_cond, timeout=5)
			except asyncio.TimeoutError:
				checkstart = True
			else:
				if (response_message.content == 'stop'):
					await message.channel.send("Game abandoned. Thanks for calling me :D")
					self.playing_cardgame = False
					return
			
			if (checkstart == True):
				logger.info("Game starts at %s" % int(time.time()))
				await message.channel.send("Music start!")
				time.sleep(1)
				break

		# posx = [100, 125, 150, 175, 200, 225, 250, 275, 300]
		# posy = [200, 225, 250, 275, 300, 325, 350, 350, 375, 400, 425, 450, 475, 500, 525, 550]
		
		x_range = [100, 512 - diff_size[diff]]
		y_range = [200, 720 - diff_size[diff]]
		network_timeout = 0
		stop = False
		dirpath = tempfile.mkdtemp()

		for count in range(0, card_num):
			card_max = MAX_SIF_CARDS

			async with message.channel.typing():
				while (network_timeout < 5):
					random_num = random.randint(1, card_max)
					url = 'http://schoolido.lu/api/cards/%s' % (random_num)
					logger.info('Searched %s' % (url))
					async with aiohttp.ClientSession() as session:
						async with session.get(url) as r:
							if r.status == 404:
								card_max = card_max / 2
								pass
							elif r.status == 200:
								js = await r.json()
								if 'detail' in js:
									card_max = card_max / 2
								else:
									selected_idol = js['idol']['name']
									if (selected_idol in SIF_IDOL_NAMES.values()):
										img = 'http:%s' % (js['card_image'])
										selected_card = js['id']
										if img == "http:None":
											img = 'http:%s' % (js['card_idolized_image'])
										logger.info('Found %s' % (img))
										break
									else:
										pass
							else:
								logger.info('Network timed out.')
								network_timeout += 1
								time.sleep(5)
				
				if network_timeout == 5:
					await message.channel.send('```Something wrong with this API. Please contact bot owner```')
					self.playing_cardgame = False
					return

				fd = urllib.request.urlopen(img)
				image_file = io.BytesIO(fd.read())
				im = Image.open(image_file)
				path = "%s/%s.png" % (dirpath, selected_card)
				im.save(path)

				#Crop image and send
				x = random.randint(*x_range)
				y = random.randint(*y_range)
				area = (x, y, x+diff_size[diff], y+diff_size[diff])
				cropped_img = im.crop(area)

				temp_path = "%s/%s_cropped.png" % (dirpath, selected_card)
				cropped_img.save(temp_path)

				await message.channel.send("Question %d of %d. Guess who?" % (count + 1, card_num), file=discord.File(temp_path))

			start = int(time.time())
			logger.info("Question %d at %s" % (count + 1, int(time.time())))
			strresult = ""
			while True:
				if (int(time.time()) - start) >= 15:
					checktimeout = True
				try:
					response_message = await self.wait_for('message', check=_cond, timeout=15)
				except asyncio.TimeoutError:
					response_message = None
				if (checktimeout == True) or (not response_message):
					logger.info("Time out.")
					checktimeout = False
					await message.channel.send("Time out! Here's the answer:\n%s, Card No.%s" % (selected_idol, selected_card), file=discord.File(path))
					break
				answ = response_message.content.lower()
				if (answ in SIF_NAME_LIST and (SIF_IDOL_NAMES[answ].lower() == selected_idol.lower())):
					await message.channel.send("10 points for %s\n%s, Card No.%s" % (response_message.author.display_name, selected_idol, selected_card), file=discord.File(path))
					if response_message.author.display_name not in userinfo:
						userinfo[response_message.author.display_name] = 0
					userinfo[response_message.author.display_name] += 10
					for x in userinfo:
						strresult += "%s: %s\n" % (x, userinfo[x])
					await message.channel.send("Round %d result:\n```prolog\n%s```" % (count + 1, strresult))
					time.sleep(2)
					break
				elif answ == "stop" and (response_message.author == user1st or self.check_owner(response_message)):
					stop = True
					break
				elif (answ in SIF_NAME_LIST):
					await message.channel.send("%s is not correct. Try again." % answ)
			
			if stop == True:
				await message.channel.send("Ok. The game stopped!")
				break

			if count + 1 != card_num:
				await message.channel.send("Here comes the next question!")
			time.sleep(1)

		shutil.rmtree(dirpath, ignore_errors=True)

		strresult = ""
		for x in userinfo:
			strresult += "%s: %s\n" % (x, userinfo[x])

		await message.channel.send("Final result:\n```prolog\n%s```" % (strresult))
		await message.channel.send("Thanks for playing :)))")

		self.playing_cardgame = False

	async def cmd_lyricgame(self, message, round_num, *args):
		"""
		Play Love Live!! lyric guessing game
		You will get 10 points for the first line, and -2 for each printed line. 5 lines maximum
		You have 45 seconds to guess the song. Each hint will be printed out with the cost of 2 points
		If the bot stucks, try {command_prefix}flush to clear its cache
		Run {command_prefix}songgame update to update the database (for the bot's owner)
		Command group: Games
		Usage:
			{command_prefix}lyricgame round_num [diff]
			- round_num: Number of rounds to play
			- diff:
				+ normal/n: from the first line to the last line of the song, sequentially
				+ hard/h: random lines of the song
			Normal diff by default

			"hint" to show a hint, including
				"hint letter": -2 points
				"hint word": -3 points
			"stop" to stop the game (for who called the game :D)

			Just type the answer without prefix :D
		Example:
			~lyricgame 10 hard
			~lyricgame 1
		"""
		if round_num.lower() == 'update':
			if self.check_owner(message):
				self._create_song_list()
				await message.channel.send('```css\nDatabase updated```')
			else:
				await message.channel.send('```prolog\nHm... You don\'t have permission to use that :(```')
			return

		song_cache = os.path.join('game_cache', 'songs')
		song_list = os.path.join('game_cache', 'song_list')
		if not os.path.exists(song_list):
			songs_available = self._create_song_list()
		else:
			with open(song_list, mode='r') as f:
				songs_available = f.readlines()
		
		try:
			if self.playing_lyricgame:
				await message.channel.send("The game is currently being played. Enjoy!")
				return
		except AttributeError:
			self.playing_lyricgame = True

		self.playing_lyricgame = True

		try:
			round_num = int(round_num)
			if round_num <= 0:
				raise ValueError
		except ValueError:
			await message.channel.send("Please type number of rounds correctly")
			self.playing_roundgame = False
			return

		def _cond(m):
			return m.channel == message.channel

		if round_num > 50:
			checktimeout = False
			checkproceed = False
			start = int(time.time())
			await message.channel.send("You really wanna play %s rounds? .-. Hm... Type `y` to proceed in 10 seconds, or `n` to quit" % card_num)

			while True:
				if (int(time.time() - start) >= 5):
					checktimeout = True
				try:
					response_message = await self.wait_for('message', check=_cond, timeout=10)
				except asyncio.TimeoutError:
					checktimeout = True
				else:
					if response_message.content == 'y':
						checktimeout = True
						checkproceed = True
					elif response_message.content == 'n':
						checktimeout = True

				if checktimeout:
					break
			
			if not checkproceed:
				await message.channel.send("Next time choose a smaller number of rounds :D")
				self.playing_lyricgame = False
				return

		normal_diff = ['normal', 'n']
		hard_diff = ['hard', 'h']
		diffs = [*normal_diff, *hard_diff]

		if not args:
			diff = 'normal'
		else:
			diff = args[0]
			if diff in diffs:
				pass
			else:
				await message.channel.send("Diff %s not found .-." % diff)
				self.playing_lyricgame = False
				return		   

		user1st = message.author
		userinfo = {user1st.display_name: 0}
		struserlist = ""
		strresult = ""
		
		await message.channel.send("Game starts in 5 seconds. Be ready!")
		checkstart = False
		checktimeout = False
		start = int(time.time())
		logger.info("Game called at %s" % (start))
		
		while True:
			if (int(time.time()) - start >= 5):
				checkstart = True
			try:
				response_message = await self.wait_for('message', check=_cond, timeout=5)
			except asyncio.TimeoutError:
				checkstart = True
			else:
				if (response_message.content == 'stop'):
					await message.channel.send("Game abandoned. Thanks for calling me :D")
					self.playing_lyricgame = False
					return
			
			if (checkstart == True):
				logger.info("Game starts at %s" % int(time.time()))
				await message.channel.send("Music start!")
				time.sleep(1)
				break

		stop = False

		for count in range(0, round_num):
			async with message.channel.typing():
				song_url = random.choice(songs_available)
				r = requests.get(song_url)
				soup =  BeautifulSoup(r.content, 'html5lib')

				song_name = soup.find('h1', {'class': 'page-header__title'}).text.strip()

				poem = soup.find_all('div', {'class': 'poem'})[0]
				lyrics = poem.text.strip()

				lines = list(filter(lambda f: f != '', lyrics.split('\n')))

				if diff in hard_diff:
					start_line = random.randint(2, len(lines) - 7)
				elif diff in normal_diff:
					start_line = 0

				await message.channel.send("Question %d of %d:" % (count + 1, round_num))

			start = int(time.time())
			logger.info("Question %d at %s" % (count + 1, int(time.time())))
			strresult = ""
			points = 12
			lines = iter(lines[start_line:start_line + 5])
			_lyrics = ''
			hint_arr = list(map(lambda x: ''.join(['-' for y in x]), song_name.split(' ')))
			while True:
				t = int(time.time()) - start
				if t % 10 == 0:
					points -= 2
					_lyrics += '♬ %s ♬\n' % (next(lines))
					await message.channel.send(_lyrics)
				
				elif t >= 45:
					checktimeout = True
				
				try:
					response_message = await self.wait_for('message', check=_cond, timeout=15)
				except asyncio.TimeoutError:
					continue
				
				if (checktimeout == True):
					logger.info("Time out.")
					checktimeout = False
					await message.channel.send("Time out! Here's the answer: **%s**" % (song_name))
					break
				answ = response_message.content.lower()
				if answ == "stop" and (response_message.author == user1st or self.check_owner(response_message)):
					stop = True
					break
				if answ == 'hint':
					await message.channel.send('''```python
Hm... What hint will you choose?\n
hint letter (-2 points) - a random letter in every word of song name (e.g. -N-- H-------) \n
hint word (-3 points) - a random word of song name (e.g. Snow)
					```''')
				elif answ.startswith('hint '):
					htype = answ.replace('hint ', '')
					if htype == 'word':
						_ = song_name.split(' ')
						while True:
							r = random.randint(0, len(_) - 1)
							if _[r] not in hint_arr and r != '':
								break
						hint_arr[r] = song_name.split(' ')[r]
						await message.channel.send(f'Word hint for u: {" ".join(hint_arr)}')
						subtract_points = 3
					if htype == 'letter':
						for i, e in enumerate(hint_arr):
							if '-' not in e:
								continue
							r = random.randint(0, len(e) - 1)
							if e[r] != '-':
								continue
							c = song_name.split(' ')[i][r] 
							try:
								s = e[:r] + c + e[r + 1:]
							except IndexError:
								s = e[:r] + c
							hint_arr[i] = s
						await message.channel.send(f'Letter hint for u: {" ".join(hint_arr)}')
						subtract_points = 2
					if response_message.author.display_name not in userinfo:
						userinfo[response_message.author.display_name] = 0
					userinfo[response_message.author.display_name] -= subtract_points
				if normalize_text(answ.strip()) == normalize_text(song_name.strip()):
					await message.channel.send("That's right! %s.\n%s points for %s" % (song_name, points, response_message.author.display_name))
					if response_message.author.display_name not in userinfo:
						userinfo[response_message.author.display_name] = 0
					userinfo[response_message.author.display_name] += points

					for x in userinfo:
						strresult += "%s: %s\n" % (x, userinfo[x])
					await message.channel.send("Round %d result:\n```prolog\n%s```" % (count + 1, strresult))
					time.sleep(2)
					break

			if stop == True:
				await message.channel.send("Ok. The game stopped!")
				break

			if count + 1 != round_num:
				await message.channel.send("Here comes the next question!")
			time.sleep(1)

		strresult = ""
		for x in userinfo:
			strresult += "%s: %s\n" % (x, userinfo[x])

		await message.channel.send("Final result:\n```prolog\n%s```" % (strresult))
		await message.channel.send("Thanks for playing :)))")

		self.playing_lyricgame = False

#
	async def cmd_songgame(self, message, round_num, *args):
		"""
		Play Love Live!! song guessing game
		A random part of a Love Live!! song will be played.
		You will have 45 seconds to guess what song is that.
		If the bot stucks, try {command_prefix}flush to clear its cache
		If you don't hear anything, try leave the voice channel & join again
		Run {command_prefix}songgame update to update the database (for the bot's owner)
		Command group: Games
		Usage:
			{command_prefix}songgame round_num [diff]
			- round_num: Number of rounds to play
			- diff:
				+ easy/e: 20 seconds of that song
				+ normal/n: 15 seconds
				+ hard/h: 10 seconds
				+ extra/ex: 5 seconds
			Normal diff by default

			"hint" to show a hint, including
				"hint letter": -2 points
				"hint word": -3 points
			"stop" to stop the game (for who called the game :D)

			Just type the answer without prefix :D
		Example:
			~songgame 10 hard
			~songgame 1
		"""
		if round_num.lower() == 'update':
			if self.check_owner(message):
				self._create_song_list()
				await message.channel.send('```css\nDatabase updated```')
			else:
				await message.channel.send('```prolog\nHm... You don\'t have permission to use that :(```')
			return

		if self.voice_client:
			if self.voice_client.is_playing():
				await message.channel.send('```prolog\nI\'m busy playing some music now :(```')

		if not self.voice_client:
			r = await self.cmd_join(message)
			if r['error']:
				return

		song_cache = os.path.join('game_cache', 'songs')
		song_list = os.path.join('game_cache', 'song_list')
		if not os.path.exists(song_list):
			songs_available = self._create_song_list()
		else:
			with open(song_list, mode='r') as f:
				songs_available = f.readlines()
				
		try:
			if self.playing_songgame:
				await message.channel.send("The game is currently being played. Enjoy!")
				return
		except AttributeError:
			self.playing_songgame = True

		# if not self.is_connected():

		try:
			round_num = int(round_num)
			if round_num <= 0:
				raise ValueError
		except ValueError:
			await message.channel.send("Please type number of rounds correctly")
			self.playing_songgame = False
			return

		def _cond(m):
			return m.channel == message.channel

		if round_num > 50:
			checktimeout = False
			checkproceed = False
			start = int(time.time())
			await message.channel.send("You really wanna play %s rounds? .-. Hm... Type `y` to proceed in 10 seconds, or `n` to quit" % round_num)

			while True:
				if (int(time.time() - start) >= 5):
					checktimeout = True
				try:
					response_message = await self.wait_for('message', check=_cond, timeout=10)
				except asyncio.TimeoutError:
					checktimeout = True
				else:
					if response_message.content == 'y':
						checktimeout = True
						checkproceed = True
					elif response_message.content == 'n':
						checktimeout = True

				if checktimeout:
					break
			
			if not checkproceed:
				await message.channel.send("Next time choose a smaller number of rounds :D")
				self.playing_songgame = False
				return
		
		easy_diff = ['easy', 'e']
		normal_diff = ['normal', 'n']
		hard_diff = ['hard', 'h']
		extra_diff = ['extra', 'ex']
		durations = {
			'e': 20,
			'easy': 20,
			'n': 15,
			'normal': 15,
			'h': 10,
			'hard': 10,
			'ex': 5,
			'extra': 5
		}
		diffs = [*easy_diff, *normal_diff, *hard_diff, *extra_diff]

		if not args:
			diff = 'normal'
		else:
			diff = args[0]
			if diff in diffs:
				pass
			else:
				await message.channel.send("Diff %s not found .-." % diff)
				self.playing_songgame = False
				return

		duration = durations[diff]

		user1st = message.author
		userinfo = {user1st.display_name: 0}
		struserlist = ""
		strresult = ""
		
		await message.channel.send("Game starts in 5 seconds. Be ready!")
		checkstart = False
		checktimeout = False
		start = int(time.time())
		logger.info("Game called at %s" % (start))
		
		while True:
			if (int(time.time()) - start >= 5):
				checkstart = True
			try:
				response_message = await self.wait_for('message', check=_cond, timeout=5)
			except asyncio.TimeoutError:
				checkstart = True
			else:
				if (response_message.content == 'stop'):
					await message.channel.send("Game abandoned. Thanks for calling me :D")
					self.playing_songgame = False
					return
			
			if (checkstart == True):
				logger.info("Game starts at %s" % int(time.time()))
				await message.channel.send("Music start!")
				time.sleep(1)
				break

		stop = False

		for count in range(0, round_num):
			await message.channel.send(f'Preparing question {count + 1} of {round_num}...')
			
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

			song_length = td.previous_sibling.text.strip()
			seconds = int(song_length[-2:])
			minutes = int(song_length[:-3])
			total_seconds = minutes * 60 + seconds

			song_onclick = song_file.find('button').attrs['onclick']
			song_url = re.search('"videoUrl":"(.*?)"', song_onclick)[1]

			song_r = requests.get(song_url)
			song_data = song_r.content
			file_name = ''.join(e for e in song_name if e.isalnum())
			with open(os.path.join(song_cache, file_name + '.ogg'), mode='wb+') as f:
				f.write(song_data)

			time_start = random.randint(0, total_seconds - duration)

			subprocess.run(['ffmpeg', '-i', os.path.join(song_cache, file_name + '.ogg'), '-ss', str(time_start), '-to', str(time_start + duration), '-c', 'copy', os.path.join(song_cache, 'file.ogg'), '-y'])

			# source = discord.PCMAudio(io.BytesIO(song_data))
			source = discord.FFmpegPCMAudio(os.path.join(os.getcwd(), song_cache, 'file.ogg'), executable='ffmpeg')

			await message.channel.send('What is this song?')
			
			self.voice_client.play(source)
			
			start = int(time.time())
			logger.info("Question %d at %s" % (count + 1, int(time.time())))
			strresult = ""
			points = 10
			hint_arr = list(map(lambda x: ''.join(['-' for y in x]), song_name.split(' ')))
			while True:
				t = int(time.time()) - start
				if t >= 45:
					checktimeout = True
				
				try:
					response_message = await self.wait_for('message', check=_cond, timeout=45)
				except asyncio.TimeoutError:
					checktimeout = True
				
				if (checktimeout == True):
					logger.info("Time out.")
					checktimeout = False
					await message.channel.send("Time out! Here's the answer: **%s**" % (song_name))
					break
				answ = response_message.content.lower()
				if answ == "stop" and (response_message.author == user1st or self.check_owner(response_message)):
					stop = True
					break
				if answ == 'hint':
					await message.channel.send('''```python
Hm... What hint will you choose?\n
hint letter (-2 points) - a random letter in every word of song name (e.g. -N-- H-------) \n
hint word (-3 points) - a random word of song name (e.g. Snow)
					```''')
				elif answ.startswith('hint '):
					htype = answ.replace('hint ', '')
					if htype == 'word':
						_ = song_name.split(' ')
						while True:
							r = random.randint(0, len(_) - 1)
							if _[r] not in hint_arr and r != '':
								break
						hint_arr[r] = song_name.split(' ')[r]
						await message.channel.send(f'Word hint for u: {" ".join(hint_arr)}')
						subtract_points = 3
					if htype == 'letter':
						for i, e in enumerate(hint_arr):
							if '-' not in e:
								continue
							r = random.randint(0, len(e) - 1)
							if e[r] != '-':
								continue
							c = song_name.split(' ')[i][r] 
							try:
								s = e[:r] + c + e[r + 1:]
							except IndexError:
								s = e[:r] + c
							hint_arr[i] = s
						await message.channel.send(f'Letter hint for u: {" ".join(hint_arr)}')
						subtract_points = 2
					if response_message.author.display_name not in userinfo:
						userinfo[response_message.author.display_name] = 0
					userinfo[response_message.author.display_name] -= subtract_points
				if normalize_text(answ.strip()) == normalize_text(song_name.strip()):
					await message.channel.send("That's right! %s.\n%s points for %s" % (song_name, points, response_message.author.display_name))
					if response_message.author.display_name not in userinfo:
						userinfo[response_message.author.display_name] = 0
					userinfo[response_message.author.display_name] += points

					for x in userinfo:
						strresult += "%s: %s\n" % (x, userinfo[x])
					await message.channel.send("Round %d result:\n```prolog\n%s```" % (count + 1, strresult))
					time.sleep(2)
					break

			if stop == True:
				await message.channel.send("Ok. The game stopped!")
				break
			
			if self.voice_client.is_playing():
				self.voice_client.stop()

			if count + 1 != round_num:
				await message.channel.send("Here comes the next question!")
			time.sleep(1)

		strresult = ""
		for x in userinfo:
			strresult += "%s: %s\n" % (x, userinfo[x])

		await message.channel.send("Final result:\n```prolog\n%s```" % (strresult))
		await message.channel.send("Thanks for playing :)))")

		await self.cmd_leave(message)

		self.playing_songgame = False

		shutil.rmtree(song_cache)
		os.mkdir(os.path.join('game_cache', 'songs'))

#