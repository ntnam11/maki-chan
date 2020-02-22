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

import aiohttp
import discord
import yaml
from PIL import Image

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

class Games:
	def __init__(self):
		pass

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
				elif (answ == "stop" and response_message.author == user1st):
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

	async def cmd_songgame(self, message, round_num, *args):
		"""
		Play Love Live!! song guessing game
		You will get 10 points for the first line, and -2 for each printed line. 5 lines maximum
		You have 45 seconds to guess the song. Each hint will be printed out with the cost of 2 points
		If the bot stucks, try {command_prefix}flush to clear its cache
		Command group: Games
		Usage:
			{command_prefix}songgame round_num [diff]
			- round_num: Number of rounds to play
			- diff:
				+ normal/n: from the first line to the last line of the song, sequentially
				+ hard/h: random lines of the song
			Normal diff by default

			"hint" to show a hint, including
				"hint center": -1 point
				"hint letter": -2 points
				"hint word": -3 points
			"stop" to stop the game (for who called the game :D)

			Just type the answer without prefix :D
		Example:
			~songgame 10 hard
			~songgame 1
		"""
		try:
			if self.playing_songgame:
				await message.channel.send("The game is currently being played. Enjoy!")
				return
		except AttributeError:
			self.playing_songgame = True

		self.playing_songgame = True

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
				self.playing_songgame = False
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
				self.playing_songgame = False
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
					self.playing_songgame = False
					return
			
			if (checkstart == True):
				logger.info("Game starts at %s" % int(time.time()))
				await message.channel.send("Music start!")
				time.sleep(1)
				break

		stop = False
		song_folder = os.path.join(os.getcwd(), 'lyrics')
		song_list = os.listdir(song_folder)

		for count in range(0, round_num):
			async with message.channel.typing():
				choice = random.choice(song_list)
				with open(os.path.join(song_folder, choice), encoding='utf-8') as f:
					song_info = yaml.load(f, Loader=yaml.SafeLoader)
				
				lyrics = song_info['lyrics']
				song_name = song_info['name']
				alt_name = []
				if song_info['alt_name']:
					alt_name = list(map(lambda f: f.replace(' ', ''), song_info['alt_name']))
				song_name_jp = song_info['name_jp']
				center = song_info['center']
				hints = song_info['hints']

				lines = list(filter(lambda f: f != '', lyrics.split('\n')))

				if diff in hard_diff:
					start_line = random.randint(2, len(lines) - 7)
				elif diff in normal_diff:
					start_line = 0

				await message.channel.send("Question %d of %d:" % (count + 1, round_num))

			start = int(time.time())
			logger.info("Question %d at %s" % (count + 1, int(time.time())))
			strresult = ""
			hint = iter(hints)
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
				if (answ == "stop" and response_message.author == user1st):
					stop = True
					break
				if answ == 'hint':
					await message.channel.send('''```python
						Hm... What hint will you choose?\n
						hint center (-1 point) - name of the center of this song\n
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
					if htype == 'center':
						await message.channel.send(f'The center of this song is {center}-chan')
						subtract_points = 1
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
				a = answ.replace(' ', '')
				found = False
				highest_ratio = 0
				for match in [
					song_name.replace(' ', '').lower(),
					song_name_jp.replace(' ', '').lower(),
					*alt_name
				]:
					if a == match:
						found = True
					else:
						if match.startswith(a):
							highest_ratio = max(highest_ratio, difflib.SequenceMatcher(None, a, answ, match).ratio())
				if found:
					await message.channel.send("That's right! %s.\n%s points for %s" % (song_name, points, response_message.author.display_name))
					if response_message.author.display_name not in userinfo:
						userinfo[response_message.author.display_name] = 0
					userinfo[response_message.author.display_name] += points

					for x in userinfo:
						strresult += "%s: %s\n" % (x, userinfo[x])
					await message.channel.send("Round %d result:\n```prolog\n%s```" % (count + 1, strresult))
					time.sleep(2)
					break
				
				# ratio = difflib.SequenceMatcher(None, answ, song_name).quick_ratio()
				if (highest_ratio >= 0.9):
					await message.channel.send("%s? Almost there!" % answ)

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

		self.playing_songgame = False
