from contextlib import asynccontextmanager

class DiscordClient:
    def __init__(self):
        pass

class DiscordUser:
    def __init__(self, display_name='Test user'):
        self.display_name = display_name
        pass

class DiscordChannel:
    def __init__(self):
        pass

    async def send(self, msg, *args, **kwargs):
        print(f'Send message to channel: {msg}')

    @asynccontextmanager
    async def typing(*args, **kwargs):
        print('Typing...')
        yield

class DiscordMessage:
    def __init__(self, author=DiscordUser(), content='', channel=DiscordChannel()):
        self.author = author
        self.content = content
        self.channel = channel

