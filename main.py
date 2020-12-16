import os
from time import perf_counter
from discord.ext import commands, tasks
from dotenv import load_dotenv
from Subcribe import Subcribe
from Schedule import Schedule
from Database import Database
from Admin import Admin
import discord

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
bot_owner = 296008737515110400

# Set prefix for bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='+', intents=intents)

# Initiate
database = Database()
admin_service = Admin(database)
schedule = Schedule(database)
subcribe = Subcribe(database, schedule, bot)


@tasks.loop(seconds=1.0)
async def task_loop():
    if await schedule.is_time_to_run_schedule_sync_service():
        # await schedule.schedule_update_service()
        pass

    if await schedule.is_time_to_run_cleanup_service():
        await schedule.multi_page_schedule_cleanup_service()

    if await subcribe.is_time_to_run_service():
        await subcribe.reminder_service(admin_service.guild_directory)


@bot.event
async def on_ready():
    # Show connected guilds
    print(f'\n{bot.user.name} is connected to the following guilds:')
    guilds = bot.guilds
    for g in guilds:
        print(f'{g.name} | (id: {g.id})')
    print()

    # Check connection with DB
    if await database.check_connection() is True:
        print("DB Connection OK!")
    else:
        raise ConnectionError('Could not connect to the database')

    # Load Schedule
    result, items_loaded = await schedule.load()
    if result is True:
        print(f'Schedule successfully loaded: {items_loaded} runs loaded')
    else:
        raise ConnectionError('Could not connect to the database')

    print('Getting initiated guilds')
    await admin_service.load()

    print('Loading subcriptions')
    await subcribe.load()

    print('Starting services')
    if task_loop.is_running() is False:
        await task_loop.start()


@bot.event
async def on_reaction_add(reaction, user):
    if user.id == bot.user.id:
        return

    if await schedule.is_multi_page_session(reaction):
        await schedule.multi_page_schedule_reaction_listener(reaction, user)


@bot.command(name='admin')
async def admin(ctx, *args):
    if ctx.author.id == bot_owner or ctx.author.id == ctx.guild.owner_id or await admin_service.is_guild_admin(ctx):
        t1 = perf_counter()
        if args[0].lower() == 'init':
            if admin_service.if_guild_init(ctx.guild.id) is False:
                await admin_service.start(ctx)
            else:
                if admin_service.if_registered_channel(ctx):
                    await ctx.send('This guild has already been initialized')
        elif args[0].lower() == 'give_admin' and len(args) == 2:
            if ctx.author.id == bot_owner or ctx.author.id == ctx.guild.owner_id:
                result = await admin_service.give_admin(ctx)
                if result is True:
                    new_admin_name = ctx.message.mentions[0].name
                    await ctx.send(f'{new_admin_name} can now use admin commands')
                else:
                    guild = ctx.guild.name
                    assigner = ctx.author.name
                    mentions = ctx.message.mentions
                    print(f'Issues giving admin role: {guild} | assigner: {assigner} | mentions: {mentions}')
        elif args[0].lower() == 'am_i_admin':
            if await admin_service.is_guild_admin(ctx):
                await ctx.message.add_reaction('✅')
        elif args[0].lower() == 'blacklist' and len(args) == 2:
            await admin_service.blacklist(bot_owner, ctx.guild.owner_id, ctx, args)
        elif args[0].lower() == 'permit' and len(args) == 2:
            await admin_service.permit(bot_owner, ctx.guild.owner_id, ctx, args)
        elif args[0].lower() == 'resync':
            await schedule.schedule_update_service()
        elif args[0].lower() == 'fake_sch':
            result = False
            text = 'ERROR in the format of the commands: +admin fake_sch "(new_date)"'
            if len(args) == 2:
                result, text = await schedule.generate_fake_schedule(new_date=args[1])
            elif len(args) == 1:
                result, text = await schedule.generate_fake_schedule()

            await ctx.send(f'```{text}```')

            if result is True:
                await schedule.schedule_update_service()
                await ctx.message.add_reaction('✅')
            else:
                await ctx.message.add_reaction('❌')
        elif args[0].lower() == 'mute':
            subcribe.mute = True
        elif args[0].lower() == 'unmute':
            subcribe.mute = False
        t2 = perf_counter()
        print(f'Execute time for admin action: {(t2 - t1) * 1000:0.4f}ms')
    else:
        print(f'{ctx.author} tried to use admin command')


@bot.command(name='sub', help='Add yourself to the ping squad')
async def add(ctx, *args):
    if admin_service.if_guild_init(ctx.guild.id):
        if admin_service.if_registered_channel(ctx) or not admin_service.is_user_blacklisted(ctx):
            t1 = perf_counter()
            if len(args) < 1:
                await subcribe.help(ctx)
            elif args[0].lower() == 'all':
                t1 = perf_counter()
                await subcribe.sub(ctx, args, schedule, sub_all=True)
                t2 = perf_counter()
            elif args[0].lower() == 'list':
                await subcribe.list_subs(ctx)
            else:
                await subcribe.sub(ctx, args, schedule)
            t2 = perf_counter()
            print(f'Execute time for sub: {(t2 - t1) * 1000:0.4f}ms')
    else:
        await ctx.send('Guild or bot owner please run \'+init\' command')


@bot.command(name='unsub', help='Remove yourself from the ping squad')
async def remove(ctx, *args):
    if admin_service.if_guild_init(ctx.guild.id):
        t1 = perf_counter()
        if admin_service.if_registered_channel(ctx) or not admin_service.is_user_blacklisted(ctx):
            if len(args) < 1 or len(args) > 1:
                await subcribe.help(ctx)
            elif args[0].lower() == 'all':
                await subcribe.unsub(ctx, args, schedule, sub_all=True)
            elif args[0].lower() == 'purge':
                await subcribe.purge(ctx)
            else:
                await subcribe.unsub(ctx, args, schedule)
        t2 = perf_counter()
        print(f'Execute time for unsub: {(t2 - t1) * 1000:0.4f}ms')

    else:
        await ctx.send('Guild or bot owner please run \'+init\' command')


@bot.command(name='schedule', help='See GDQ schedule')
async def get_schedule(ctx, *args):
    if admin_service.if_guild_init(ctx.guild.id):
        if admin_service.if_registered_channel(ctx) or not admin_service.is_user_blacklisted(ctx):
            if len(args) == 0:
                await schedule.get(ctx)
            else:
                await schedule.get(ctx, filter_schedule=True, args=args)
    else:
        await ctx.send('Guild or bot owner please run \'+init\' command')


@bot.command(name='purge')
async def purge(ctx, *args):
    if ctx.author.id == bot_owner:
        await database.purge_subs()


bot.run(TOKEN)
