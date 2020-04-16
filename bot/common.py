import discord
import logging
from functools import wraps

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
    try:
        await channel.send(message)
    except discord.errors.HTTPException:
        found = False
        for i, e in enumerate(message[l:]):
            if e == sep:
                found = True
                break
        if not found:
            i = l
        else:
            i += l
        await channel.send(message[:i] + suffix)
        await channel.send(prefix + message[i:])

def owner_only(func):
    @wraps(func)
    async def target_func(self, message, *args):
        if str(message.author.id) == str(self.owner_id):
            await func(self, message, *args)
        else:
            await message.channel.send('```autohotkey\nSorry. You do not have enough permissions to call this command (´･ω･`)```')

    return target_func