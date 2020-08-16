import asyncio
import json
import os
import discord
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

        for run in data_handler.schedule:
            delay_delta = await data_handler.get_delay_delta()
            run_datetime = (data_handler.strtodatetime(run["time"])) + delay_delta
            reminder_time = (run_datetime - timedelta(hours=0, minutes=5))
            end_of_run = (run_datetime + timedelta(hours=0, minutes=run["length"]))

            if reminder_time < datetime.now() < end_of_run and run["reminded"] is False:
                # ping squad
                run["reminded"] = True
                await data_handler.save_schedule()
                time_remaining = data_handler.diffdates(datetime.now(), run_datetime)
                reminder_embed = discord.Embed(title="STARTING SOON - GAMES DONE QUICK 2020",
                                               url="https://gamesdonequick.com/schedule",
                                               description=" Please click title for full schedule", color=0x466e9c)
                reminder_embed.set_thumbnail(url="https://gamesdonequick.com/static/res/img/gdqlogo.png")
                reminder_embed.add_field(
                    name=f'{run["game"]} ({run["run"]}) in {time_remaining}',
                    value=f'By: {run["runners"]} | '
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
                    print(channel)
                    channel_to_send_to = bot.get_channel(channel)
                    if channel_to_send_to is not None:
                        role = discord.utils.get(channel_to_send_to.guild.roles, name=data_handler.ping_role_name)
                        message_content = ""
                        if role is not None:
                            message_content = role.mention
                        message_content = message_content + " https://www.twitch.tv/gamesdonequick"
                        await channel_to_send_to.send(message_content, embed=reminder_embed)

                break
            elif datetime.now() > end_of_run:
                # remove run
                data_handler.schedule.remove(run)
                await data_handler.save_schedule()

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
