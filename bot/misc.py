import aiohttp
import discord
import random
import logging

from .common import *

logger = logging.getLogger('root.misc')

class Misc:
	def __init__(self):
		return 

	async def cmd_say(self, message, *args):
		'''
		Make the bot say something
		Command group: Misc
		Usage: {command_prefix}say [text]
		Example: {command_prefix}say Hello!
		'''
		await message.channel.send(' '.join(args))
		await delete_message(message)
	
	async def cmd_bigtext(self, message, *args):
		"""
		Display a BIGTEXT (´･ω･`)
		Command group: Misc
		Usage: {command_prefix}bigtext [text]
		Example: {command_prefix}bigtext woohoo
		"""
		result = ""
		
		for word in args.lower():
			for s in word:
				if s != ' ':
					result += ":regional_indicator_%s:" % s
			result += " "

		await message.channel.send(result)
		await delete_message(message)

	async def cmd_lenny(self, message, *args):
		'''
		Sends a ( ͡° ͜ʖ ͡°)
		Command group: Misc
		Usage: {command_prefix}lenny
		Example: {command_prefix}lenny
		'''
		await message.channel.send('( ͡° ͜ʖ ͡°)')
		await delete_message(message)

	async def cmd_cat(self, message, *args):
		'''
		Sends a random cat from random.cat
		Command group: Misc
		Usage: {command_prefix}cat
		Example: {command_prefix}cat
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

		embed = discord.Embed()
		embed.set_image(url=url)
		await message.channel.send(embed=embed)

	async def cmd_choose(self, message, choice, *args):
		'''
		Help u to choose something lmao
		Don't blame me if something goes wrong ┐(‘～`；)┌
		Command group: Misc
		Usage: {command_prefix}choose [option 1], [option 2],...
		Example: {command_prefix}choose friend, like, love
		'''

		if args is not None:
			text = ' '.join([choice, *args])
			choices = text.split(', ')
		else:
			await message.channel.send(f'```prolog\nOh cmon. Give me some more options ┐(‘～`；)┌```')
			return
		
		result = random.choice(choices)
			
		await message.channel.send(f'Well, I choose **{result}**!')

	async def cmd_calc(self, message, expr, *args):
		'''
		Help u to calculate something lmao
		Command group: Misc
		Usage: {command_prefix}calc [expression]
		Example: {command_prefix}calc 123*(456-789)
		'''
		expr = ''.join([expr, *args]).replace(' ', '')
		for s in expr:
			if not s.isdigit() and s not in ['+', '-', '*', '/', 'x', '^']:
				await message.channel.send(f'```fix\nSyntax Error. Please try again ┐(‘～`；)┌```')
				return
		r = expr.replace('x', '*').replace('^', '**')
		try:
			result = eval(r)
		except Exception as e:
			await message.channel.send(f'```fix\nSyntax Error. Please try again ┐(‘～`；)┌```')
			return
		await message.channel.send(f'```python\n{result}```')