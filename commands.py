import re
import aiohttp
from textwrap import dedent

import discord

async def get_pic(img_type):
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
            Command group: Pics
            Usage: {command_prefix}[action] [mention / text]
            Example: ~[action] / ~[action] @_Kotori_
            '''
            url = await get_pic(func_obj['type'])
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
        return target_func
    else:
        async def notarget_func(message, *args):
            '''
            Sends a pic
            Command group: pics
            Usage: {command_prefix}[action]
            Example: ~[action]
            '''
            url = await get_pic(func_obj['type'])
            if url['error']:
                await message.channel.send(url['message'])
            else:
                e = discord.Embed(title='{0} {1}'.format(message.author.name, func_obj['text']))
                e.set_image(url=url['url'])
                await message.channel.send(embed=e)
        return notarget_func

class Commands:
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
        
        else:
            if 'cmd_' + command in dir(self):
                e.title = command
                desc = dedent(getattr(self, 'cmd_' + command).__doc__)
                if '[action]' in desc:
                    desc = desc.replace('[action]', command)
                e.description = desc
            else:
                await message.channel.send('Command not found')
                return

        await message.channel.send(embed=e)
    
    async def cmd_say(self, message, *args):
        '''
        Make the bot say something
        Command group: Misc
        Usage: {command_prefix}say [text]
        Example: ~say Hello!
        '''
        await message.channel.send(' '.join(args))
    
    async def cmd_bigtext(self, message, text):
        """
        Display a BIGTEXT :D
        Command group: Misc
        Usage: {command_prefix}bigtext [text]
        Example: ~bigtext woohoo
        """
        result = ""
        
        for word in text:
            for s in word:
                if s != ' ':
                    result += ":regional_indicator_%s:" % s
            result += " "

        await message.channel.send(result)

    async def cmd_lenny(self, message, *args):
        '''
        Sends a ( ͡° ͜ʖ ͡°)
        Command group: pics
        Usage: {command_prefix}lenny
        Example: ~lenny
        '''
        await message.channel.send('( ͡° ͜ʖ ͡°)')

    async def cmd_cat(self, message, *args):
        '''
        Sends a random cat from random.cat
        Command group: Misc
        Usage: {command_prefix}cat
        Example: ~cat
        '''
        url = "https://aws.random.cat/meow" % (img_type)
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
