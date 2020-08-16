import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from DataHandler import DataHandler

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set prefix for bot
bot = commands.Bot(command_prefix='+')

# Initiate data handler
data_handler = DataHandler()


@bot.event
async def on_ready():
    # Show connected guilds
    print(f'{bot.user.name} is connected to the following guilds:')
    guilds = bot.guilds
    for g in guilds:
        print(f'{g.name} | (id: {g.id})')
    print()

    print('Loading user list...')
    load_result = await data_handler.load_from_file()
    if load_result is True:
        print('Done')
        print(data_handler.user_list)
    else:
        print('Error loading user list!')

    print('Loading schedule...')
    load_result = await data_handler.load_schedule()
    if load_result is True:
        print('Done')
        print(data_handler.schedule)
    else:
        print('Error loading schedule!')

@bot.command(name='add', help='Add yourself to the ping squad')
async def add(ctx, *args):
    result = await data_handler.add_user(ctx.author)
    if result is True:
        await ctx.send(f'{ctx.author} has been added to the GDQ ping list')
        print(data_handler.user_list)


@bot.command(name='remove', help='Remove yourself from the ping squad')
async def remove(ctx, *args):
    result = await data_handler.remove_user(ctx.author)
    if result is True:
        await ctx.send(f'{ctx.author} has been removed from the GDQ ping list')
        print(data_handler.user_list)


@bot.command(name='mute', help='Mute Notifications')
async def mute(ctx, *args):
    result = await data_handler.mute(ctx.author)
    if result is True:
        await ctx.send(f'{ctx.author} has MUTED the GDQ ping')
        print(data_handler.user_list[str(ctx.author.id)])


@bot.command(name='unmute', help='Unmute Notifications')
async def unmute(ctx, *args):
    result = await data_handler.unmute(ctx.author)
    if result is True:
        await ctx.send(f'{ctx.author} has UNMUTED the GDQ ping')
        print(data_handler.user_list[str(ctx.author.id)])


@bot.command(name='schedule', help='See GDQ schedule')
async def schedule(ctx, *args):
    await data_handler.get_schedule(ctx)


@bot.command(name='hi', help='-')
async def hi(ctx, *args):
    await ctx.send("Hello!")


bot.run(TOKEN)
