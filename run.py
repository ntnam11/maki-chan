import discord
import logging

from client import MainClient

prefix = '~'
token = 'MzM0MzA0NjE4NDc5NzQ3MDcy.XTk8fw.JQe99GEJfUNdyYA3hFs9vR2PVDw'

client = MainClient({
    'prefix': prefix,
    'version': 'beta v0.0.1'
})
client.run(token)