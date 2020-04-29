import logging
import os
import time
from functools import wraps
from urllib.parse import quote, unquote

import discord
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger('root.common')

SIF_IDOL_NAMES = {
	'eli': 'Ayase Eli', 'rin': 'Hoshizora Rin', 'umi': 'Sonoda Umi', 'hanayo': 'Koizumi Hanayo', 'hana': 'Koizumi Hanayo',
	'honoka': 'Kousaka Honoka', 'honk': 'Kousaka Honoka', 'kotori': 'Minami Kotori', 'birb': 'Minami Kotori', 'maki': 'Nishikino Maki', 'nozomi': 'Toujou Nozomi', 'nico': 'Yazawa Nico',
	'chika': 'Takami Chika', 'riko': 'Sakurauchi Riko', 'you': 'Watanabe You', 'yoshiko': 'Tsushima Yoshiko', 'yohane': 'Tsushima Yoshiko',
	'ruby': 'Kurosawa Ruby', 'hanamaru': 'Kunikida Hanamaru', 'maru': 'Kunikida Hanamaru', 'mari': 'Ohara Mari', 'dia': 'Kurosawa Dia', 'kanan': 'Matsuura Kanan',
	'alpaca': 'Alpaca', 'shiitake': 'Shiitake', 'uchicchi': 'Uchicchi',
	"chika's mother": "Chika's mother", "honoka's mother": "Honoka's mother", "kotori's mother": "Kotori's mother", "maki's mother": "Maki's mother", "nico's mother": "Nico's mother",
	'cocoa': 'Yazawa Cocoa', 'cocoro': 'Yazawa Cocoro', 'cotarou': 'Yazawa Cotarou',
	'ayumu': 'Uehara Ayumu', 'setsuna': 'Yuki Setsuna', 'shizuku': 'Osaka Shizuku',
	'karin': 'Asaka Karin', 'kasumi': 'Nakasu Kasumi', 'ai': 'Miyashita Ai',
	'rina': 'Tennoji Rina', 'kanata': 'Konoe Kanata', 'emma': 'Emma Verde',
}
SIF_NAME_LIST = [
	'eli', 'rin', 'hanayo', 'hana', 'honoka', 'honk', 'kotori', 'birb', 'maki', 'umi', 'nozomi', 'nico',
	'chika', 'riko', 'you', 'yoshiko', 'ruby', 'hanamaru', 'maru', 'mari', 'dia', 'kanan', 'yohane',
	'alpaca', 'shiitake', 'uchicchi',
	"chika's mother", "honoka's mother", "kotori's mother", "maki's mother", "nico's mother",
	'cocoa', 'cocoro', 'cotarou',
	'ayumu', 'ai', 'setsuna', 'kanata', 'karin', 'emma', 'rina', 'shizuku', 'kasumi',
]

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

async def delete_message(message):
	try:
		await message.delete()
	except discord.Forbidden:
		logger.error('Delete message failed due to no permission')
		pass

async def send_long_message(channel, message, prefix='', suffix='', sep=' '):
	l = int(len(message) / 2)
	if len(message + prefix + suffix + sep) < 2000:
		await channel.send(message)
	else:
		found = False
		for i, e in enumerate(message[l:]):
			if e == sep:
				found = True
				break
		if not found:
			i = l
		else:
			i += l
		await send_long_message(channel, message[:i] + suffix, prefix=prefix, suffix=suffix, sep=sep)
		await send_long_message(channel, prefix + message[i:], prefix=prefix, suffix=suffix, sep=sep)

def owner_only(func):
	@wraps(func)
	async def target_func(self, message, *args):
		if str(message.author.id) == str(self.owner_id):
			await func(self, message, *args)
		else:
			await message.channel.send('```fix\nSorry. You do not have enough permissions to call this command (´･ω･`)```')

	return target_func

def create_song_list():
	resource_url = 'https://love-live.fandom.com/wiki/Songs_BPM_List'
	r = requests.get(resource_url)

	soup = BeautifulSoup(r.content, 'html5lib')
	
	tables = soup.find_all('table', {'class': 'wikitable'})		
	songs_available = []
	for table in tables:
		songs = table.find_all('a')
		song_urls = []

		for song in songs:
			song_urls.append('https://love-live.fandom.com' + song.attrs['href'])
		
		songs_available.extend(song_urls)

	with open(os.path.join('game_cache', 'song_additional')) as f:
		content = f.readlines()

	for line in content:
		l = line.strip()
		if l != '':
			songs_available.append(l)

	songs_available = list(set(songs_available))
	
	with open(os.path.join('game_cache', 'song_list'), mode='w+') as f:
		f.write('\n'.join(songs_available))

	return songs_available

async def get_song_url(client, message, query):
	song_list = os.path.join('game_cache', 'song_list')
	if not os.path.exists(song_list):
		songs_available = create_song_list()
	else:
		with open(song_list, mode='r') as f:
			songs_available = f.readlines()
	
	found = []
	for song_url in songs_available:
		url = song_url.strip()
		qq = quote(query.replace(' ', '_')).lower()
		if qq in url.replace('https://love-live.fandom.com/wiki/', '').lower():
			found.append(url)

	if len(found) == 0:
		await message.channel.send('```prolog\nHm... I can\'t find this song in the database (´ヘ｀()```')
		return ''
	elif len(found) == 1:
		return found[0]
	elif len(found) > 30:
		await message.channel.send('```prolog\nHm... I found too many results. Please be more specific (´ヘ｀()```')
		return ''
	else:
		strfound = ''
		for i, url in enumerate(found):
			song_name = unquote(url).replace("https://love-live.fandom.com/wiki/", "").replace("_", " ")
			strfound += f'{i}. {song_name}\n'
		strfound += 'c. Cancel```'

		await message.channel.send(f'I\'ve found {len(found)} songs contains **{query}**. Which one do you like?```prolog\n{strfound}')

		def _cond(m):
			return m.channel == message.channel and m.author == message.author

		start = int(time.time())
		checktimeout = False
		while True:
			if (int(time.time()) - start) >= 30:
				checktimeout = True

			try:
				response_message = await client.wait_for('message', check=_cond, timeout=30)
			except asyncio.TimeoutError:
				response_message = None

			if (checktimeout == True) or (not response_message):
				await message.channel.send('```fix\nTimeout. Request aborted```')
				return ''

			resp = response_message.content.lower()

			if (resp == 'c'):
				await message.channel.send('```css\nOkay. Nevermind```')
				return ''

			if not resp.isdigit() or int(resp) not in range(0, len(found)):
				await message.channel.send('```fix\nPlease type the correct number```')

			else:
				break

		return found[int(resp)]

def message_voice_filter(func):
	@wraps(func)
	async def target_func(self, message, *args, **kwargs):
		author_voice_ch = message.author.voice
		if author_voice_ch is not None:
			author_voice_ch = author_voice_ch.channel
		if message.author.id != self.owner_id and (not author_voice_ch or author_voice_ch != self.voice_channel):
			await message.channel.send('```fix\nSorry. You aren\'t in the same voice channel with me (´･ω･`)```')
		else:
			await func(self, message, *args, **kwargs)

	return target_func
