import os
import discord
import youtube_dl
import aiohttp
import asyncio
import logging
import random
import re
import time
import datetime

from bs4 import BeautifulSoup

from .common import *

ytdl_format_options = {
	'format': 'bestaudio/best',
	'extractaudio': True,
	'audioformat': 'mp3',
	'outtmpl': 'audio_cache/%(id)s',
	'restrictfilenames': True,
	'noplaylist': True,
	'nocheckcertificate': True,
	'ignoreerrors': False,
	'logtostderr': False,
	'quiet': True,
	'no_warnings': True,
	'default_search': 'auto'
}

logger = logging.getLogger('Music')

class Song:
	def __init__(self, url, title, youtube=True, source='', downloaded=False):
		if youtube:
			if not url.startswith('https'):
				self.id = url
				self.url = 'https://www.youtube.com/watch?v=' + url
			else:
				self.id = url.split('?v=')[1]
				self.url = url
		else:
			self.url = url

		self.title = url
		
		if title is not None:
			self.title = title

		self.downloading = False
		self.downloaded = downloaded
		self.file_path = ''
		self.source = source

	def _download(self, cls):

		download = True
		
		if self.id in os.listdir(cls.music_cache_dir):
			download = False

		if not self.downloaded:

			print(f'Downloading... {self.url}')

			with youtube_dl.YoutubeDL(ytdl_format_options) as ydl:
				self.downloading = True
				try:
					info = ydl.extract_info(self.url, download=download)
				except youtube_dl.utils.DownloadError:
					return {'error': True}
				self.title = info.get('title')
				self.id = info.get('id')
			
			self.downloaded = True
			self.downloading = False

			return {'error': False}

class MusicPlayer:
	def __init__(self):
		self.music_queue = []
		self.radio_requests = {}

	async def _youtube_search(self, query, **kwargs):
		url = 'https://www.googleapis.com/youtube/v3/search'
		params = {
			'part': 'snippet',
			'maxResults': 10,
			'q': query,
			'type': 'video',
			'key': self.youtube_apikey,
			**kwargs
		}

		result = []

		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params) as r:
				if r.status == 200:
					js = await r.json()
					for r in js['items']:
						result.append({
							'id': r['id']['videoId'],
							'title': r['snippet']['title']
						})
				else:
					return {'error': True, 'message': 'Network error. Please try again later'}

		return {'error': False, 'result': result}

	async def _process_query(self, *args, source='', **kwargs):
		query = ' '.join(args)
		if query.startswith('youtube') or query.startswith('yt'):
			try:
				query = query.split(' ')[1]
			except IndexError:
				return

		if 'title' in kwargs:
			title = kwargs['title']
		else:
			title = None
		
		if query.startswith('https://www.youtube.com'):
			s = Song(query, title, source=source)
			r = await self._add_to_queue(s)
			if r['error']:
				await self.voice_text_channel.send('```fix\This video is not available (*´д｀*)```')
				return
		
		else:
			r = await self._youtube_search(query, maxResult=10)
			if not r['error']:
				i = 0
				while True:
					s = r['result'][i]
					song = Song(s['id'], s['title'], source=source)
					ar = await self._add_to_queue(song)
					if not ar['error']:
						break
					i += 1

	async def _add_to_queue(self, song_obj):
		self.music_queue.append(song_obj)
		
		if song_obj.source == 'search':
			await self.voice_text_channel.send(f'Adding {song_obj.url}...')
		else:
			await self.voice_text_channel.send(f'```css\nAdding {song_obj.url}...```')

		for song in self.music_queue:
			if not song.downloaded and not song.downloading:
				logger.debug('Downloading %s' % song.id)
				r = song._download(self)
				if r['error']:
					return r
			else:
				logger.debug('Skip downloading %s' % song.id)

		await self.voice_text_channel.send('```css\nAdded %s```' % song.title)

		await self._process_queue()

		return {'error': False}

	async def _process_queue(self):
		if self.force_stop_music:
			return

		if self.music_loop:
			self.music_queue.insert(0, self.current_song)

		if len(self.music_queue) == 0:
			self.current_song = None
			return

		if not self.voice_client:
			return

		if self.voice_client.is_playing():
			return
		
		while True:
			try:
				self.current_song = self.music_queue.pop(0)
				if self.current_song is None:
					pass
				else:
					break
			except IndexError:
				break
		self.current_song.file_path = os.path.join(self.music_cache_dir, self.current_song.id)
		
		game = discord.Game(self.current_song.title)
		await self.change_presence(activity=game)
		
		source = discord.FFmpegPCMAudio(self.current_song.file_path, executable='ffmpeg')

		if not self.music_loop:
			await self.voice_text_channel.send('```fix\nNow playing: %s```' % self.current_song.title)

		try:
			self.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self._process_queue(), self.loop))
		except discord.errors.ClientException:
			await self.voice_client.connect()
			self.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self._process_queue(), self.loop))

class Music(MusicPlayer):
	def __init__(self):
		return super(Music, self).__init__()
	
	async def cmd_join(self, message, *args, internal=False):
		'''
		Join a voice channel
		Command group: Music
		Usage: {command_prefix}join
		Example: {command_prefix}join
		'''
		if self.voice_client:
			if self.voice_client.is_playing():
				await message.channel.send('```prolog\nSorry. I\'m busy playing some music now (´д｀*)```')
				return {'error': True}

		try:
			self.voice_channel = message.author.voice.channel
		except AttributeError:
			await message.channel.send('```css\nPlease join a voice channel first (´･ω･`)```')
			return {'error': True}
			
		try:
			self.voice_client = await self.voice_channel.connect()
			if not self.voice_client:
				self.voice_client = self.voice_clients[0]
		except asyncio.TimeoutError:
			await message.channel.send('```css\nCould not connect to the voice channel in time```')
			return {'error': True}
		except discord.ClientException:
			if not internal:
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
	
	@message_voice_filter
	async def cmd_leave(self, message, *args):
		'''
		Leave a voice channel
		Command group: Music
		Usage: {command_prefix}leave
		Example: {command_prefix}leave
		'''
		if self.playing_radio:
			self.force_stop_radio = True
		if self.current_song is not None:
			self.force_stop_music = True
		if not self.voice_client and not self.voice_channel:
			# await message.channel.send('```prolog\nHm... I haven\'t joined any voice channel```')
			return
		if self.voice_client:
			if self.voice_client.is_playing():
				self.voice_client.stop()
			await self.voice_client.disconnect()
		if message:
			await message.channel.send('```prolog\nLeft "%s"```' % self.voice_channel.name)
		self.voice_channel = None
		self.voice_client = None
		self.playing_radio = False
		self.force_stop_radio = False
		self.radio_cache = []
		self.force_stop_music = False
		self.radio_requests = {}

	@message_voice_filter
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
			{command_prefix}play snow halation
			{command_prefix}play https://www.youtube.com/watch?v=g1p5eNOsl7I
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

	@message_voice_filter
	async def cmd_search(self, message, query, *args):
		'''
		Search a video on youtube, up to 10 results
		Command group: Music
		Usage: {command_prefix}search [query]
		Example: {command_prefix}search snow halation
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
			return m.channel == message.channel and m.author == message.author

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
			await self._process_query('https://www.youtube.com/watch?v=' + r['result'][int(resp)]['id'], title=r['result'][int(resp)]['title'], source='search')

	async def cmd_np(self, message, *args):
		'''
		Show what's being played in voice channel
		Command group: Music
		Usage: {command_prefix}np
		Example: {command_prefix}np
		'''
		if self.playing_radio:
			await message.channel.send('```fix\nNow playing non-stop Love Live!! songs```')
			return

		if self.current_song:
			await message.channel.send('```fix\nNow playing: %s```\n%s' % (self.current_song.title, self.current_song.url))
		else:
			await message.channel.send('```fix\nNothing is being played at the moment. Wanna add some?```')

	@message_voice_filter
	async def cmd_skip(self, message, *args):
		'''
		Skip current playing song in voice channel
		If there are more than 2 members in the same voice channel, a skip voting system will be used
		Command group: Music
		Usage: {command_prefix}skip
		Example: {command_prefix}skip
		'''
		if not self.playing_radio and not self.current_song:
			await message.channel.send('```fix\nNothing to skip at the moment```')
			return

		if self.voice_channel is not None:
			member_count = 0

			for mem in self.voice_channel.members:
				if not mem.voice.self_deaf:
					member_count += 1

			if member_count > 2:
				votes_needed = min(3, int(member_count / 2) + 1)
				m = await message.channel.send(f'```css\nSkip requested. React with ➕ to skip this song ({votes_needed} needed)```')
				await m.add_reaction('➕')
				
				msg_check_id = m.id

				start_time = time.time()
				
				skip = False

				while True:
					m = await message.channel.fetch_message(msg_check_id)
					
					if int(time.time() - start_time) > 10:
						break

					reaction_count = 0
					async for user in m.reactions[0].users():
						if user in self.voice_channel.members and not user.voice.self_deaf:
							reaction_count += 1

					if reaction_count >= votes_needed:
						skip = True
						break

					time.sleep(.5)

				if not skip:
					await message.channel.send('```css\nHm... Skip request aborted```')
					return
				else:
					await message.channel.send('```css\nOkay. Changing media...```')

		if self.playing_radio:
			if self.voice_client:
				if self.voice_client.is_playing():
					self.voice_client.stop()
			# if len(self.music_queue) > 0:
			# 	await self.cmd_llradio(message, internal=True)
			# return
		elif self.current_song:
			self.voice_client.stop()
			if not self.music_loop:
				await message.channel.send('```fix\nSkipped %s```' % self.current_song.title)
				await self._process_queue()
			else:
				await message.channel.send('```fix\nWell, you may need to turn off looping before skipping```')

	async def cmd_queue(self, message, *args):
		'''
		Show music queue
		Command group: Music
		Usage: {command_prefix}queue
		Example: {command_prefix}queue
		'''
		if len(self.music_queue) == 0:
			await message.channel.send('```css\nNo song in queue. Wanna add some?```')
			return

		str_result = '```css\n'

		for i, result in enumerate(self.music_queue):
			str_result += '%s. %s\n' % (i + 1, result.title)
		
		str_result += '```'

		await message.channel.send(str_result)

	@message_voice_filter
	async def cmd_clear(self, message, *args):
		'''
		Clear the music queue
		Command group: Music
		Usage: {command_prefix}clear
		Example: {command_prefix}clear
		'''
		self.music_queue = []
		await message.channel.send('```css\nQueue cleared```')

	@message_voice_filter
	async def cmd_stop(self, message, *args):
		'''
		Force stop Love Live!! radio
		Command group: Music
		Usage: {command_prefix}stop
		Example: {command_prefix}stop
		'''
		if self.playing_radio:
			self.force_stop_radio = True
		
		if self.current_song is not None:
			self.force_stop_music = True

		if self.voice_client:
			if self.voice_client.is_playing():
				self.voice_client.stop()

		await message.channel.send('```css\nDone```')

		self.force_stop_radio = False
		self.radio_cache = []
		self.music_queue = []
		self.music_loop = False
		self.force_stop_music = False
		self.playing_radio = False

	async def cmd_loop(self, message, *args):
		'''
		Loop a song
		Command group: Music
		Usage: {command_prefix}loop
		Example: {command_prefix}loop
		'''
		if self.playing_radio:
			await message.channel.send('```fix\nWell, u can\'t loop a radio bruh (ﾟヮﾟ)```')
			return
		
		if not self.voice_client:
			await message.channel.send('```fix\nNothing to loop at the moment```')

		self.music_loop = not self.music_loop

		if self.music_loop:
			await message.channel.send('```prolog\nLoop: on```')
		else:
			await message.channel.send('```prolog\nLoop: off```')

	async def cmd_llradio(self, message, *args, internal=False, retry_count=0):
		'''
		Play a random Love Live! song (including Sunshine, Nijigasaki & Saint Snow)
		If you want another Love Live! Radio instance, consider adding another me: https://discordapp.com/api/oauth2/authorize?client_id=697328604186411018&permissions=70569024&scope=bot
		Command group: Music
		Usage:
			{command_prefix}llradio
		Example:
			{command_prefix}llradio
		'''
		if not internal:
			if self.playing_radio:
				await message.channel.send('```prolog\nI\'m playing radio now щ(ಠ益ಠщ)```')
				return
			if self.current_song is not None:
				self.force_stop_music = True
			if not self.voice_client and not self.voice_channel:
				pass
			else:
				if self.voice_client.is_playing():
					self.voice_client.stop()

		if retry_count >= 3:
			await message.channel.send('```fix\nError trying to play some music. Please contact the bot\'s owner (*´д｀*)```')
			return

		song_cache = os.path.join('game_cache', 'songs')
		song_list = os.path.join('game_cache', 'song_list')
		if not os.path.exists(song_list):
			songs_available = create_song_list()
		else:
			with open(song_list, mode='r') as f:
				songs_available = f.readlines()
		
		if len(self.radio_cache) >= 100:
			self.radio_cache.pop(0)

		self.playing_radio = True

		if self.force_stop_radio:
			return

		if not self.voice_client:
			r = await self.cmd_join(message)
			if r['error']:
				return

		self.check_sleep(message)

		mem_count = len(self.voice_channel.members)
		deaf_count = 0
		for mem in self.voice_channel.members:
			if mem.voice.self_deaf:
				deaf_count += 1

		if mem_count == 1 or deaf_count == mem_count - 1:
			await message.channel.send('```fix\nIt seems no one is listening to me. I\'m leaving ┐(‘～`；)┌```')
			await self.cmd_leave(message)
			return

		song_info = None

		async with aiohttp.ClientSession() as session:
			while True:
				if len(self.music_queue) > 0:
					song_info = self.music_queue.pop(0)
					break
				else:
					song_url = random.choice(songs_available)
					if song_url in self.radio_cache:
						continue
					else:
						self.radio_cache.append(song_url)

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
			
			if song_info is None:
				song_length = td.previous_sibling
				song_name = song_length.previous_sibling.text.strip()

				song_onclick = song_file.find('button').attrs['onclick']
				song_url = re.search('"videoUrl":"(.*?)"', song_onclick)[1]

			else:
				song_name = song_info.title
				song_url = song_info.url

			async with session.get(song_url) as r:
				with open(os.path.join('game_cache', 'radio.ogg'), mode='wb+') as f:
					f.write(await r.read())

		game = discord.Game(song_name)
		await self.change_presence(activity=game)

		source = discord.FFmpegPCMAudio(os.path.join(os.getcwd(), 'game_cache', 'radio.ogg'), executable='ffmpeg')

		md = random.choice(['fix', 'css', 'prolog', 'autohotkey', '', 'coffeescript', 'md', 'ml', 'cs', 'diff', 'tex'])

		if md in ['diff']:
			prefix = '!'
		elif md in ['tex']:
			prefix = '$'
		else:
			prefix = '#'

		await message.channel.send(f'```{md}\n{prefix} Now playing: {song_name}```')

		try:
			self.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.cmd_llradio(message, internal=True, retry_count=retry_count), self.loop))
		except discord.errors.ClientException:
			logger.warning('Cannot play music. Trying again...')
			await self.cmd_join(message, internal=True)
			self.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.cmd_llradio(message, internal=True, retry_count=retry_count + 1), self.loop))

	async def cmd_request(self, message, query, *args):
		'''
		Request a song on Love Live! radio (including Sunshine, Nijigasaki & Saint Snow)
		If there are more than 2 non-self-deafened members, only 1 request can be made each 15 minutes
		Command group: Music
		Usage:
			{command_prefix}request [song_name] (idol/off vocal/mix name)
		Example:
			{command_prefix}request spicaterrible
			{command_prefix}request spicaterrible (kotori)
			{command_prefix}request spicaterrible (off vocal)
			{command_prefix}request aishiteru banzai (prepro piano mix)
		'''
		if message.author.id in self.radio_requests:
			last_request = self.radio_requests[message.author.id]
			if self.voice_channel:
				
				member_count = 0

				for mem in self.voice_channel.members:
					if not mem.voice.self_deaf:
						member_count += 1

				if member_count > 2:
					if time.time() - last_request < 900:
						next_request = datetime.datetime.fromtimestamp(last_request) + datetime.timedelta(hours=self.timezone, minutes=15)
						await message.channel.send(f'```fix\nSorry. You can only request a song every 15 minutes. Your next request available at {next_request.strftime("%Y-%m-%d %H:%M:%S")}```')
						return

		q = ' '.join([query, *args]).lower()
		singer = ''
		off_vocal = False

		o = max(q.find('off vocal'), q.find('(off vocal)'))
		if o != -1:
			off_vocal = True
			q = q.replace('(off vocal)', '').replace('off vocal', '')

		r = re.search('\((.*?)\)', q)

		if r is not None:
			singer = r[1]
			q = q.replace(r[0], '')

		url = await get_song_url(self, message, q.strip())
		if url == '':
			return

		async with aiohttp.ClientSession() as session:
			async with session.get(url) as r:
				soup = BeautifulSoup(await r.read(), 'html5lib')

		song_name = soup.find('h1', {'class': 'page-header__title'}).text.strip()

		song_files = soup.find_all('div', {'class': 'ogg_player'})
		song_name_list = []
		song_url_list = []

		for song_file in song_files:
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

			if t is not None:
				if t.attrs['title'].lower() == 'radio drama':
					continue

			song_length = td.previous_sibling
			song_name = song_length.previous_sibling.text.strip()
			song_onclick = song_file.find('button').attrs['onclick']
			song_url = re.search('"videoUrl":"(.*?)"', song_onclick)[1]

			song_name_list.append(song_name)
			song_url_list.append(song_url)

		found = False

		for i, song_name in enumerate(song_name_list):
			if singer != '':
				if singer.lower() in song_name.lower():
					found = True
					break
			elif off_vocal:
				if 'off vocal' in song_name.lower():
					found = True
					break
			else:
				found = True
				break
		
		if found:
			song_info = Song(song_url_list[i], song_name, youtube=False)
		else:
			await message.channel.send(f'```fix\nHm... I can\'t find this version. Please try another (*´д｀*)```')
			return

		self.music_queue.append(song_info)

		self.radio_requests[message.author.id] = time.time()

		if not self.playing_radio:
			await self.cmd_llradio(message)
		else:
			await message.channel.send(f'```css\nAdded {song_info.title}```')