import asyncio
import io
import logging
import os
import random
import shutil
import tempfile
import time
import urllib.parse
import re
import gc
import subprocess

import aiohttp
import discord
import yaml
from PIL import Image
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
from bs4 import BeautifulSoup

from .common import *
from .exceptions import *

logger = logging.getLogger('root.Games')

class _Song:
	def __init__(self, url):
		self.text = url
		self.attrs = {
			'href': url
		}

class Games:
	def __init__(self):
		pass

	async def cmd_cardgame(self, message, card_num, *args):
		"""
		Play LLSIF card guessing game
		If the bot stucks, try {command_prefix}flush to clear its cache
		Command group: Games
		Usage:
			{command_prefix}cardgame [as] card_num [diff] [custom_dimension]
			- as: All-stars
			- card_num: Number of rounds to play
			- diff:
				+ easy/e: image size 300x300
				+ normal/n: image size 200 x 200
				+ hard/h: image size 150 x 150
				+ extreme/ex: image size 100 x 100
				+ custom/c: image size {custom_dimension} x {custom_dimension} 
			- custom_dimension: an integer between 10 - 400
			Normal diff by default

			stop to stop the game (for who called the game (´･ω･`))

			Just type the answer without prefix (´･ω･`)
			
			Idol names including: 
				maki, rin, hanayo, hana, kotori, birb, honoka, honk, umi, eli, nozomi, nico,
				ruby, hanamaru, maru, yoshiko, yohane, you, chika, riko, mari, kanan, dia,
				ayumu, ai, setsuna, kanata, karin, emma, rina, shizuku, kasumi,
				and some support characters

			You must answer in 15 seconds (´･ω･`)
		Example:
			{command_prefix}cardgame 10 ex
			{command_prefix}cardgame 1
		"""
		try:
			if self.playing_cardgame:
				await message.channel.send('```css\nThe game is currently being played. Enjoy!```')
				return
		except AttributeError:
			self.playing_cardgame = True

		all_stars = False
		if card_num == 'as':
			all_stars = True
			if not args:
				pass
			else:
				card_num = args[0]
				if len(args) == 1:
					args = None
				else:
					args = args[1:]

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
				await message.channel.send("Next time choose a smaller number of rounds (´･ω･`)")
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
		
		if all_stars:
			source = 'Love Live! School Idol Festival ALL STARS'
		else:
			source = 'Love Live! School Idol Festival'
		await message.channel.send(f'```prolog\nSource: {source}\nDifficulty: {diff.capitalize()}\nImage size: {diff_size[diff]} x {diff_size[diff]}\nNumber of rounds: {card_num}```\nGame starts in 5 seconds. Be ready!')

		checkstart = False
		checktimeout = False
		start = int(time.time())
		logger.debug("Game called at %s" % (start))

		game = discord.Game('Card Game with friends')
		await self.change_presence(activity=game)

		self.playing_cardgame = True

		await asyncio.sleep(5)

		x_range = [100, 512 - diff_size[diff]]
		y_range = [200, 720 - diff_size[diff]]
		stop = False
		dirpath = tempfile.mkdtemp()

		for count in range(0, card_num):
			card_max = self.config['max_sif_cards']

			async with message.channel.typing():
				retries = 0
				async with aiohttp.ClientSession() as session:
					while True:
						try:
							network_timeout = 0
							while network_timeout < 5:
								random_num = random.randint(1, card_max)
								url = f'https://schoolido.lu/api/cards/{random_num}'
								if all_stars:
									url = 'https://idol.st/allstars/cards/random/'
								logger.debug(f'Searched {url}')
								async with session.get(url) as r:
									if r.status == 404:
										card_max = card_max / 2
										pass
									elif r.status == 200:
										if not all_stars:
											js = await r.json()
											if 'detail' in js:
												card_max = card_max / 2
											else:
												selected_idol = js['idol']['name']
												if (selected_idol in SIF_IDOL_NAMES.values()):
													key = random.choice(['card_image', 'card_idolized_image'])
													img = f'https:{js[key]}'
													selected_card = js['id']
													if img == "http:None" or img == "https:None":
														img = 'https:%s' % (js['card_idolized_image'])
													logger.debug(f'Found {img}')
													break
										else:
											soup = BeautifulSoup(await r.read(), 'html5lib')
											path = r.url.path
											selected_card = re.findall(r'\d+', path)[0]
											idol = soup.find('tr', {'data-field': 'idol'})
											selected_idol = idol.find('a', {'class': None}).attrs['data-ajax-title']
											if selected_idol in SIF_IDOL_NAMES.values():
												images = soup.find_all('img', {'class': 'allstars-card-image'})
												image = random.choice(images)
												img = 'https:' + urllib.parse.quote(f"{image.attrs['src']}")
												e_rarity = soup.find('tr', {'data-field': 'rarity'}).text
												rarity = e_rarity.replace('Rarity', '').strip()
												logger.debug(f'Found {img}')
												break
									else:
										logger.warning('Network timed out.')
										network_timeout += 1
										time.sleep(3)
						
							if network_timeout == 5:
								await message.channel.send('```Something wrong with the API server. Please contact bot owner / try again later```')
								self.playing_cardgame = False
								return

							async with session.get(img) as r:
								image_file = io.BytesIO(await r.read())
							im = Image.open(image_file)
							path = "%s/%s.png" % (dirpath, selected_card)
							im.save(path)

							if all_stars:
								zoom = 640 / 1800
								rarity_x_start = {
									'rare': 500,
									'super rare': 0,
									'ultra rare': 0
								}
								rarity_x_end = {
									'rare': 1300,
									'super rare': 1800,
									'ultra rare': 1800
								}
								x_range = [int(rarity_x_start[rarity.lower()] * zoom), int(rarity_x_end[rarity.lower()] * zoom - diff_size[diff])]
								y_range = [0, int(900 * zoom - diff_size[diff])]
							x = random.randint(*x_range)
							y = random.randint(*y_range)
							area = (x, y, x+diff_size[diff], y+diff_size[diff])
							cropped_img = im.crop(area)

							temp_path = f'{dirpath}/{selected_card}_cropped.png'
							cropped_img.save(temp_path)
						except OSError:
							logger.error('Error occurred. Continue searching')
							retries += 1
							if retries == 5:
								raise
							pass
						else:
							break

				await message.channel.send(f'Question {count + 1} of {card_num}. Guess who?', file=discord.File(temp_path))

			start = int(time.time())
			logger.debug(f'Question {count + 1} at {int(time.time())}')
			strresult = ""
			while True:
				if (int(time.time()) - start) >= 15:
					checktimeout = True
				try:
					response_message = await self.wait_for('message', check=_cond, timeout=15)
				except asyncio.TimeoutError:
					response_message = None
				if (checktimeout == True) or (not response_message):
					logger.debug(f'Timed out at {int(time.time())}')
					checktimeout = False
					await message.channel.send(f'Time out! Here\'s the answer:\n{selected_idol}, Card No.{selected_card}', file=discord.File(path))
					break
				answ = response_message.content.lower()
				if (answ in SIF_NAME_LIST and (SIF_IDOL_NAMES[answ].lower() == selected_idol.lower())):
					await message.channel.send(f'10 points for {response_message.author.display_name}\n{selected_idol}, Card No.{selected_card}', file=discord.File(path))
					if response_message.author.display_name not in userinfo:
						userinfo[response_message.author.display_name] = 0
					userinfo[response_message.author.display_name] += 10
					for x in userinfo:
						strresult += "%s: %s\n" % (x, userinfo[x])
					await message.channel.send(f'Round {count + 1} result:\n```prolog\n{strresult}```')
					time.sleep(2)
					break
				elif answ == "stop" and (response_message.author == user1st or self.check_owner(response_message)):
					stop = True
					break
				elif (answ in SIF_NAME_LIST):
					await message.channel.send(f'{answ} is not correct. Try again.')
			
			if stop == True:
				logger.debug(f'Game stopped at {int(time.time())}')
				await message.channel.send("Ok. The game stopped!")
				break

			if count + 1 != card_num:
				await message.channel.send("Here comes the next question!")
			time.sleep(1)

		shutil.rmtree(dirpath, ignore_errors=True)

		strresult = ""
		sorted_name = [v[0] for v in sorted(userinfo.items(), key=lambda kv: (-kv[1], kv[0]))]
		for x in sorted_name:
			strresult += f'{x}: {userinfo[x]}\n'

		await message.channel.send(f'Final result:\n```prolog\n{strresult}```\nThanks for playing :3')

		self.playing_cardgame = False
		gc.collect()

	async def cmd_lyricgame(self, message, round_num, *args):
		"""
		Play Love Live!! lyric guessing game
		You will get 10 points for the first line, and -2 for each printed line. 5 lines maximum
		You have 45 seconds to guess the song. Each hint will be printed out with the cost of 2 points
		For special character (star, arrow, heart,...), you can use a dot "." instead
		If the bot stucks, try {command_prefix}flush to clear its cache
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
			"stop" to stop the game (for who called the game (´･ω･`))

			Just type the answer without prefix (´･ω･`)
		Example:
			{command_prefix}lyricgame 10 hard
			{command_prefix}lyricgame 1
		"""
		song_cache = os.path.join('game_cache', 'songs')
		song_list = os.path.join('game_cache', 'song_list')
		if not os.path.exists(song_list):
			songs_available = create_song_list()
		else:
			with open(song_list, mode='r') as f:
				songs_available = f.readlines()
		
		try:
			if self.playing_lyricgame:
				await message.channel.send('```css\nThe game is currently being played. Enjoy!```')
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
				await message.channel.send("Next time choose a smaller number of rounds (´･ω･`)")
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
		
		await message.channel.send(f'```prolog\nDifficulty: {diff.capitalize()}\nNumber of rounds: {round_num}```\nGame starts in 5 seconds. Be ready!')
		checkstart = False
		checktimeout = False
		start = int(time.time())
		logger.debug("Game called at %s" % (start))
				
		game = discord.Game('Lyrics Game with friends')
		await self.change_presence(activity=game)

		await asyncio.sleep(5)

		stop = False

		async with aiohttp.ClientSession() as session:
			for count in range(0, round_num):
				async with message.channel.typing():
					song_url = random.choice(songs_available)

					async with session.get(song_url.strip()) as r:
						soup =  BeautifulSoup(await r.read(), 'html5lib')
		
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
				logger.debug("Question %d at %s" % (count + 1, int(time.time())))
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
						logger.debug("Time out.")
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
		sorted_name = [v[0] for v in sorted(userinfo.items(), key=lambda kv: (-kv[1], kv[0]))]
		for x in sorted_name:
			strresult += f'{x}: {userinfo[x]}\n'

		await message.channel.send(f'Final result:\n```prolog\n{strresult}```\nThanks for playing :3')

		self.playing_lyricgame = False

		gc.collect()

#
	async def cmd_songgame(self, message, round_num, *args):
		"""
		Play Love Live!! song guessing game
		A random part of a Love Live!! song will be played.
		You will have 45 seconds to guess what song is that.
		If the bot stucks, try {command_prefix}flush to clear its cache
		If you don't hear anything, try leave the voice channel & join again
		For special character (star, arrow, heart,...), you can use a dot "." instead
		For the bot's owner:
			{command_prefix}songgame update: to update the database
			{command_prefix}songgame add [url]: to add a song
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
			"stop" to stop the game (for who called the game (´･ω･`))

			Just type the answer without prefix (´･ω･`)
		Example:
			{command_prefix}songgame 10 hard
			{command_prefix}songgame 1
		"""
		if round_num.lower() == 'update':
			if self.check_owner(message):
				create_song_list()
				await message.channel.send('```css\nDatabase updated```')
			else:
				await message.channel.send('```prolog\nHm... You don\'t have permission to use that (*´д｀*)```')
			return

		song_cache = os.path.join('game_cache', 'songs')
		song_list = os.path.join('game_cache', 'song_list')
		if not os.path.exists(song_list):
			songs_available = create_song_list()
		else:
			with open(song_list, mode='r') as f:
				songs_available = f.readlines()
				
		if round_num.lower() == 'add':
			query = ' '.join(args)
			if self.check_owner(message):
				if query not in songs_available:
					if query.startswith('https://love-live.fandom.com/wiki'):
						with open(os.path.join('game_cache', 'song_additional'), mode='a+') as f:
							f.write(query + '\n')
						await message.channel.send('```css\nSong added```')
					else:
						await message.channel.send('```prolog\nPlease give a wiki link instead ┐(‘～`；)┌```')
				else:
					await message.channel.send('```prolog\nSong existed```')
			else:
				await message.channel.send('```prolog\nHm... You don\'t have permission to use that (*´д｀*)```')
			return

		if self.voice_client:
			if self.voice_client.is_playing():
				await message.channel.send('```prolog\nI\'m busy playing some music now (*´д｀*)```')
				return

		if not self.voice_client:
			r = await self.cmd_join(message)
			if r['error']:
				return
		try:
			if self.playing_songgame:
				await message.channel.send('```css\nThe game is currently being played. Enjoy!```')
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
			await message.channel.send("```prolog\nSorry. I can only hold up to 50 songs. Pls choose a smaller number (*´д｀*)```")
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
		
		await message.channel.send(f'```prolog\nDifficulty: {diff.capitalize()}\nLength: {duration} seconds\nNumber of rounds: {round_num}```\nGame starts in 5 seconds. Be ready!')
		checktimeout = False
		logger.debug("Game called at %s" % int(time.time()))

		await asyncio.sleep(5)
		
		game = discord.Game('Song Game with friends')
		await self.change_presence(activity=game)
		
		logger.debug("Game starts at %s" % int(time.time()))
		await message.channel.send("Music start!")
		time.sleep(1)

		stop = False

		cached = []

		async with aiohttp.ClientSession() as session:
			for count in range(0, round_num):
				await message.channel.send(f'Preparing question {count + 1} of {round_num}...')
				
				while True:
					song_url = random.choice(songs_available)
					if song_url in cached:
						continue
					else:
						cached.append(song_url)
						
					async with session.get(song_url.strip()) as r:
						soup =  BeautifulSoup(await r.read(), 'html5lib')

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

				async with session.get(song_url.strip()) as r:
					song_data = await r.read()

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
				logger.debug("Question %d at %s" % (count + 1, int(time.time())))
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
						logger.debug("Time out.")
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
		sorted_name = [v[0] for v in sorted(userinfo.items(), key=lambda kv: (-kv[1], kv[0]))]
		for x in sorted_name:
			strresult += f'{x}: {userinfo[x]}\n'

		await message.channel.send(f'Final result:\n```prolog\n{strresult}```\nThanks for playing :3')

		await self.cmd_leave(message)

		self.playing_songgame = False

		shutil.rmtree(song_cache)
		os.mkdir(os.path.join('game_cache', 'songs'))

		gc.collect()
#
	
	async def cmd_scout(self, message, *args):
		"""
		Test your luck with scouting
		Command group: Games
		Usage:
			{command_prefix}scout [bt|bt10|bt25] [idol_name|muse|aqours] [1|11]
				+ {command_prefix}scout for scouting muse 11
				+ {command_prefix}scout bt [idol_name|muse|aqours] [idlz] for Blue Ticket use (default is scout bt muse)
				+ {command_prefix}scout idol_name|muse|aqours [1|11] [idlz] for gem use (default if scout 11)
		Example:
			{command_prefix}scout bt
			{command_prefix}scout kotori
			{command_prefix}scout kotori 11
		"""

		#Init variables
		idol_name = {'eli': 'Ayase Eli', 'rin': 'Hoshizora Rin', 'umi': 'Sonoda Umi', 'hanayo': 'Koizumi Hanayo',
		'honoka': 'Kousaka Honoka', 'kotori': 'Minami Kotori', 'maki': 'Nishikino Maki', 'nozomi': 'Toujou Nozomi', 'nico': 'Yazawa Nico',
		'chika': 'Takami Chika', 'riko': 'Sakurauchi Riko', 'you': 'Watanabe You', 'yoshiko': 'Tsushima Yoshiko',
		'ruby': 'Kurosawa Ruby', 'hanamaru': 'Kunikida Hanamaru', 'mari': 'Ohara Mari', 'dia': 'Kurosawa Dia', 'kanan': 'Matsuura Kanan',
		'eri': 'Ayase Eli', 'honky': 'Kousaka Honoka', 'birb': 'Minami Kotori', 'yohane': 'Tsushima Yoshiko', 'maru': 'Kunikida Hanamaru'}
		
		ubox = ['eli', 'rin', 'hanayo', 'honoka', 'kotori', 'maki', 'umi', 'nozomi', 'nico', 'hana', 'honk', 'birb']
		abox = ['chika', 'riko', 'you', 'yoshiko', 'ruby', 'hanamaru', 'mari', 'dia', 'kanan', 'yohane', 'maru']
		# nbox = ['ayumu', 'setsuna', 'shizuku', 'karin', 'kasumi', 'ai', 'rina', 'kanata', 'emma']

		if self.scouting:
			await message.channel.send('```prolog\n Chotto. I\'m busy doing some gacha now ( ﾟдﾟ)...```')
			return

		rarity = ['r', 'sr', 'ssr', 'ur']
		rarity_bt = ['sr', 'ur']
		rarity_bt10 = ['ssr', 'ur']
		rarity_bt25 = ['ur']
		rarity_dream = ['sr', 'ssr', 'ur']

		rrate = 0.8
		srrate = 0.15
		ssrrate = 0.04
		urrate = 0.01

		bturrate = 0.2
		btsrrate = 0.8

		dreamsrrate = 0.5
		dreamssrrate = 0.3
		dreamurrate = 0.2

		cardlist = []

		url = "https://schoolido.lu/api/cardids/?is_promo=False"

		#Default params
		scout_num = 11
		scout_ticket = False
		scout_ticket_num = 5
		scout_idlz = False
		scout_box = ubox

		dream = False
		failed = 0

		scout_args = list(args)

		self.scouting = True

		while len(scout_args) > 0:
			query = scout_args.pop(0)
			if query is None:
				continue
			else:
				query = query.lower()
			if query in ["bt", "bt10", "bt25"]:
				scout_ticket = True
				scout_num = 1
				if query == "bt10":
					scout_ticket_num = 10
				elif query == "bt25":
					scout_ticket_num = 25
			if query == "idlz":
				scout_idlz = True
			if query == "dream":
				dream = True
				scout_num = 11
			if query == "muse":
				scout_box = ubox
			if query == "aqours":
				scout_box = abox
			if query in ubox + abox: # + nbox:
				scout_box = query
			if query.isdigit():
				scout_num = int(query)
				if scout_num != 1 and scout_num != 11:
					scout_num = 11

		logger.debug("Box: %s - Quantity: %s - Blue ticket: %s" % (scout_box, scout_num, scout_ticket))

		if scout_box == ubox:
			url += "&idol_main_unit=%CE%BC%27s"
		elif scout_box == abox:
			url += "&idol_main_unit=aqours"
		elif scout_box in (ubox + abox): # + nbox):
			# url += "&name=%s" % idol_name[scout_box]
			url += f'&name={SIF_IDOL_NAMES[scout_box]}'
		logger.debug("URL: %s" % url)

		if scout_num == 11:
			scout = random.choices(rarity, k=11, weights=[rrate, srrate, ssrrate, urrate])
			if dream == True:
				scout = random.choices(rarity_dream, k=11, weights=[dreamsrrate, dreamssrrate, dreamurrate])
		elif scout_num == 1:
			if scout_ticket == False:
				scout = random.choices(rarity, k=1, weights=[rrate, srrate, ssrrate, urrate])
			else:
				if scout_ticket_num == 5:
					scout = random.choices(rarity_bt, k=1, weights=[btsrrate, bturrate])
				elif scout_ticket_num == 10:
					scout = random.choices(rarity_bt10, k=1, weights=[btsrrate, bturrate])
				elif scout_ticket_num == 25:
					scout = random.choices(rarity_bt25, k=1, weights=[1])

		rs = list(set(scout))
		rarity_count = {x: scout.count(x) for x in rs}

		async with message.channel.typing():
			async with aiohttp.ClientSession() as session:
				for k, v in rarity_count.items():
					async with session.get(url + f'&rarity={k}') as r:
						if r.status == 200:
							js = await r.json()
							card_num = random.choices(js, k=v)
							cardlist.extend(card_num)
						else:
							failed = 1
							logger.error("Network error.")
							await message.channel.send('```prolog\nServer Error. Please try again later (ノ_・。)```')
							self.scouting = False
							return

				result = ""
				scout_11_bg = os.path.join('assets', 'scout_bg.jpg')
				scout_11_bg_im = Image.open(scout_11_bg)

				current_result = '```css\n'
				for i, x in enumerate(cardlist):
					url = "https://schoolido.lu/api/cards/%s/" % x	
					async with session.get(url) as r:
						js = await r.json()

					card_name = js['idol']['name']
					card_rarity = js['rarity']
					card_id = js['id']
					card_set = js['translated_collection']
					card_date = js['release_date']
					card_attrb = js['attribute']
					card_skill = js['skill']
					card_hp = js['hp']
					if scout_idlz == False:
						card_img = 'https:%s' % (js['card_image'])
					else:
						card_img = 'https:%s' % (js['card_idolized_image'])

					current_result += f'#{card_id} {card_rarity} {card_name} '
					if str(card_set).lower() != "none":
						current_result += f'[{card_set}, {card_date}] '
					else:
						current_result += f'[{card_date}] '
					current_result += f'({card_attrb}, {card_skill}, HP: {card_hp})\n'
					
					if scout_num == 11:
						try:
							round_card_img = f"https:{js['round_card_image']}"
							if round_card_img is None or scout_idlz:
								raise KeyError
						except KeyError:
							round_card_img = f"https:{js['round_card_idolized_image']}"
					
						path = os.path.join('game_cache', 'scout', f'{x}.png')
						if os.path.exists(path):
							pass
						else:
							async with session.get(round_card_img) as r:
								with open(path, mode='wb+') as f:
									f.write(await r.read())

						im = Image.open(path).convert('RGBA')
						if i <= 5:
							offset = (159 + i * 160, 70)
						else:
							offset = (239 + (i - 6) * 160, 260)
						scout_11_bg_im.paste(im, offset, im)
					
					if scout_num == 1:
						embed = discord.Embed()
						embed.set_image(url=card_img)
						kwargs = {
							'embed': embed
						}

			if scout_num == 11:
				path = os.path.join('game_cache', 'scout.jpg')
				scout_11_bg_im.crop((90, 20, 1140, 420)).save(path)
				kwargs = {
					'file': discord.File(path)
				}

			game_cache_scout = os.path.join('game_cache', 'scout')
			if os.path.exists(game_cache_scout):
				shutil.rmtree(game_cache_scout)

			os.mkdir(game_cache_scout)

			await message.channel.send(current_result + '```', **kwargs)

		self.scouting = False
