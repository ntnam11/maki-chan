import discord
import youtube_dl

class MusicPlayer:
    def __init__(self):
        self.music_queue = []

    def process_query(self, query):
        if query.startswith('youtube') or query.startswith('yt'):
            try:
                query = query.split(' ')[1]
            except IndexError:
                return
        if query.startswith('https://www.youtube.com'):
            ytdl_format_options = {
                'format': 'bestaudio/best',
                'extractaudio': True,
                'audioformat': 'mp3',
                'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
                'restrictfilenames': True,
                'noplaylist': True,
                'nocheckcertificate': True,
                'ignoreerrors': False,
                'logtostderr': False,
                'quiet': True,
                'no_warnings': True,
                'default_search': 'auto',
                'source_address': '0.0.0.0'
            }
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download(['https://www.youtube.com/watch?v=BaW_jenozKc'])       
        pass

    def process_queue(self):
        pass