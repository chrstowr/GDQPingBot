import asyncio
import json
import os
import discord
import time
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path
from json import JSONDecodeError
from DataHandler import DataHandler

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set prefix for bot
bot = commands.Bot(command_prefix='+')

# Initiate data handler
data_handler = DataHandler()


async def schedule_check_clock():
    while True:
        load_occured = False
        # Refresh schedule every 10 minutes
        refresh_datetime = await data_handler.get_refresh_datetime()
        if datetime.utcnow() > refresh_datetime:
            data_handler.reload_schedule()
            new_refresh_datetime = datetime.utcnow() + timedelta(minutes=10)
            data_handler.save_refresh_datetime(new_refresh_datetime)
            await data_handler.load_schedule()
            print(f"Schedule refresh complete - {datetime.utcnow()}")

        for run in data_handler.schedule:
            run_datetime = (data_handler.strtodatetime(run["time"]))
            end_of_run = (run_datetime + timedelta(minutes=run["length"]))
            if run_datetime < datetime.utcnow() < end_of_run and run["reminded"] is False:
                # ping squad
                run["reminded"] = True
                await data_handler.save_schedule()
                reminder_embed = discord.Embed(title="GAMES DONE QUICK 2020",
                                               url="https://gamesdonequick.com/schedule", color=0x466e9c)
                reminder_embed.set_thumbnail(url="https://gamesdonequick.com/static/res/img/gdqlogo.png")
                reminder_embed.set_footer(text='Speedrun start times are subject to change')
                reminder_embed.add_field(
                    name=f'Coming up next:',
                    value=f'{run["game"]} ({run["run"]})\nBy: {run["runners"]} | '
                          f'Estimated length: {data_handler.explodeminutes(run["length"])}',
                    inline=False)

                channel_list = None

                try:
                    directory = os.path.dirname(__file__)
                    file = os.path.join(directory, 'channels.json')
                    session_data_file = Path(file)
                    with open(session_data_file, 'r') as f:
                        data = json.load(f)
                        f.close()
                        channel_list = data
                except JSONDecodeError as e:
                    print(f'{JSONDecodeError}: {e}')

                for channel in channel_list:
                    channel_to_send_to = bot.get_channel(channel)
                    if channel_to_send_to is not None:
                        role = discord.utils.get(channel_to_send_to.guild.roles, name=data_handler.ping_role_name)
                        message_content = ""
                        if role is not None:
                            message_content = role.mention
                        message_content = message_content + " https://www.twitch.tv/gamesdonequick"
                        await channel_to_send_to.send(message_content, embed=reminder_embed)

                break
            elif datetime.utcnow() > end_of_run and run["reminded"] is False:
                run["reminded"] = True

        await asyncio.sleep(30)


@bot.event
async def on_ready():
    # Show connected guilds
    print(f'{bot.user.name} is connected to the following guilds:')
    guilds = bot.guilds
    for g in guilds:
        print(f'{g.name} | (id: {g.id})')
    print()

    print('Loading schedule...')
    load_result = await data_handler.load_schedule()
    if load_result is True:
        print('Done')
    else:
        print('Error loading schedule!')

    await bot.loop.create_task(schedule_check_clock())


@bot.command(name='add', help='Add yourself to the ping squad')
async def add(ctx, *args):
    result = await data_handler.add_user(ctx.author, ctx)
    if result is True:
        await ctx.send(f'{ctx.author} has been added to the GDQ ping list')


@bot.command(name='remove', help='Remove yourself from the ping squad')
async def remove(ctx, *args):
    result = await data_handler.remove_user(ctx.author, ctx)
    if result is True:
        await ctx.send(f'{ctx.author} has been removed from the GDQ ping list')


@bot.command(name='schedule', help='See GDQ schedule')
async def schedule(ctx, *args):
    await data_handler.get_schedule(ctx)


bot.run(TOKEN)
