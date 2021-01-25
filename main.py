import os
from time import perf_counter
from discord.ext import commands, tasks
from dotenv import load_dotenv
from Subscribe import Subscribe
from Schedule import Schedule
from Help import Help
from Admin import Admin
import discord

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
bot_owner = 296008737515110400

# Set prefix for bot
intents = discord.Intents.default()
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix='+', intents=intents, help_command=None)

# Initiate
help_command = Help()
admin_service = Admin()
schedule = Schedule(bot)
subscribe = Subscribe(schedule, bot)


# Idea list:
# TODO: Detach user from guilds, create an index of what guild each user is in
# TODO: Allow sub command to work from DM
# TODO: Add VOD link command
# TODO: Change to MongoDB atlas?
# TODO: Figure out web dashboard

@tasks.loop(seconds=1.0)
async def task_loop():
    if await schedule.is_time_to_run_schedule_sync_service():
        await schedule.schedule_update_service(subscribe)

    if await schedule.is_time_to_run_cleanup_service():
        await schedule.multi_page_schedule_cleanup_service()

    if await subscribe.is_time_to_run_service():
        await subscribe.reminder_service(admin_service.guild_directory)


@bot.event
async def on_ready():
    # Show connected guilds
    print(f'\n{bot.user.name} v1.2 is connected to the following guilds:')
    guilds = bot.guilds
    for g in guilds:
        print(f'{g.name} | (id: {g.id})')
    print()

    # Load Schedule
    result, items_loaded = await schedule.load(subscribe)
    if result is True:
        print(f'Schedule successfully loaded: {items_loaded} runs loaded')
    else:
        raise FileNotFoundError('Could not load subcriptions from file')

    print('Getting initiated guilds')
    await admin_service.load()

    print('Loading subcriptions')
    await subscribe.load()

    admin_service.files_loaded = True

    print('Starting services')
    if task_loop.is_running() is False:
        await task_loop.start()


@bot.event
async def on_message(message):
    if admin_service.files_loaded is True:
        if message.guild is not None:
            if message.author.id == bot_owner or message.author.id == message.guild.owner_id or await admin_service.is_guild_admin(
                    message):
                if message.author.id == bot.user.id:
                    return

                if message.content.lower().startswith('good gdqbot'):
                    await message.add_reaction('🥰')
                    print(f'{message.author.name} ({message.guild.name}) praised the bot!')
                    await admin_service.add_praise(message)

    await bot.process_commands(message)


@bot.event
async def on_reaction_add(reaction, user):
    if admin_service.files_loaded is True:
        if user.id == bot.user.id:
            return

        if await schedule.is_multi_page_session(reaction):
            await schedule.multi_page_schedule_reaction_listener(reaction, user)


@bot.event
async def on_message_delete(message):
    # Ignore messages deleted by bot
    if message.author == bot.user:
        return

    if admin_service.files_loaded is True:
        if admin_service.if_guild_init(message.guild.id):
            if admin_service.if_registered_channel(message) or not admin_service.is_user_blacklisted(message):
                await schedule.on_message_delete_assoc_listener(message.guild.id, message.id, message.channel)


# init, give/take admin, blacklist/permit, resync, mute/unmute, stop/start
@bot.command(name='admin')
async def admin(ctx, *args):
    if admin_service.files_loaded is True:
        if ctx.author.id == bot_owner or ctx.author.id == ctx.guild.owner_id or await admin_service.is_guild_admin(ctx):
            t1 = perf_counter()
            if args[0].lower() == 'init':
                if admin_service.if_guild_init(ctx.guild.id) is False:
                    await admin_service.start(ctx, bot)
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
            elif args[0].lower() == 'take_admin' and len(args) == 2:
                if ctx.author.id == bot_owner or ctx.author.id == ctx.guild.owner_id:
                    result = await admin_service.take_admin(ctx)
                    if result is True:
                        new_admin_name = ctx.message.mentions[0].name
                        await ctx.send(f'{new_admin_name} cannot use admin commands anymore')
                    else:
                        guild = ctx.guild.name
                        assigner = ctx.author.name
                        mentions = ctx.message.mentions
                        print(f'Issue with admin _admin: {guild} | assigner: {assigner} | mentions: {mentions}')
            elif args[0].lower() == 'am_i_admin':
                if await admin_service.is_guild_admin(ctx):
                    await ctx.message.add_reaction('✅')
            elif args[0].lower() == 'blacklist' and len(args) == 2:
                await admin_service.blacklist(bot_owner, ctx.guild.owner_id, ctx, args)
            elif args[0].lower() == 'permit' and len(args) == 2:
                await admin_service.permit(bot_owner, ctx.guild.owner_id, ctx, args)
            elif args[0].lower() == 'resync':
                await schedule.schedule_update_service(subscribe)
                await ctx.message.add_reaction('✅')
            elif args[0].lower() == 'fake_sch':
                if ctx.author.id == bot_owner:
                    result = False
                    text = 'ERROR in the format of the commands: +admin fake_sch "(new_date)"'
                    if len(args) == 1:
                        result, text = await schedule.generate_fake_schedule(subscribe)

                    await ctx.send(f'```{text}```')

                    if result is True:
                        await schedule.schedule_update_service(subscribe)
                        await ctx.message.add_reaction('✅')
                    else:
                        await ctx.message.add_reaction('❌')
            elif args[0].lower() == 'mute':
                result = await admin_service.mute(ctx)
                if result is True:
                    await ctx.message.add_reaction('✅')
            elif args[0].lower() == 'unmute':
                result = await admin_service.unmute(ctx)
                if result is True:
                    await ctx.message.add_reaction('✅')
            elif args[0].lower() == 'stop':
                result = await admin_service.stop_reminders(ctx)
                if result is True:
                    await ctx.message.add_reaction('✅')
            elif args[0].lower() == 'start':
                result = await admin_service.start_reminders(ctx)
                if result is True:
                    await ctx.message.add_reaction('✅')
            elif args[0].lower() == 'roles':
                await admin_service.test_members(ctx, bot)
            elif args[0].lower() == 'check_perms':
                admin_service.check_permissions(ctx, bot)
            elif args[0].lower() == 'del_msg':
                await admin_service.delete_bot_msg(ctx, args)
            t2 = perf_counter()
            print(f'Execute time for admin action: {(t2 - t1) * 1000:0.4f}ms')
        else:
            print(f'{ctx.author} tried to use admin command')


@bot.command(name='move')
async def move(ctx, *args):
    if admin_service.files_loaded is True:
        if ctx.author.id == bot_owner or ctx.author.id == ctx.guild.owner_id:
            await admin_service.move(ctx, bot)


@bot.command(name='sub')
async def add(ctx, *args):
    if admin_service.files_loaded is True:
        if not (ctx.guild is None and isinstance(ctx.channel, discord.channel.DMChannel)):
            if ctx.guild is not None and admin_service.if_guild_init(ctx.guild.id):
                if admin_service.if_registered_channel(ctx) and not admin_service.is_user_blacklisted(ctx):
                    t1 = perf_counter()
                    if len(args) > 0:
                        if args[0].lower() == 'all':
                            t1 = perf_counter()
                            await subscribe.sub(ctx, args, schedule, sub_all=True)
                            t2 = perf_counter()
                        elif args[0].lower() == 'list':
                            await subscribe.list_subs(ctx)
                        else:
                            await subscribe.sub(ctx, args, schedule)
                    t2 = perf_counter()
                    print(f'Execute time for sub: {(t2 - t1) * 1000:0.4f}ms')
            else:
                await ctx.send('Guild or bot owner please run \'+admin init\' command')
        else:
            if args[0].lower() == 'list':
                await subscribe.list_subs(ctx, dm=True)


@bot.command(name='unsub')
async def remove(ctx, *args):
    if admin_service.files_loaded is True:
        if ctx.guild is not None and admin_service.if_guild_init(ctx.guild.id):
            t1 = perf_counter()
            if admin_service.if_registered_channel(ctx) and not admin_service.is_user_blacklisted(ctx):
                if len(args) > 0:
                    if args[0].lower() == 'all':
                        await subscribe.unsub(ctx, args, schedule, sub_all=True)
                    elif args[0].lower() == 'purge':
                        await subscribe.purge(ctx)
                    else:
                        await subscribe.unsub(ctx, args, schedule)
            t2 = perf_counter()
            print(f'Execute time for unsub: {(t2 - t1) * 1000:0.4f}ms')

        else:
            await ctx.send('Guild or bot owner please run \'+admin init\' command')


@bot.command(aliases=['upcoming', 'u'])
async def get_upcoming(ctx, *args):
    if admin_service.files_loaded is True:
        if not (ctx.guild is None and isinstance(ctx.channel, discord.channel.DMChannel)):
            if admin_service.if_guild_init(ctx.guild.id):
                if admin_service.if_registered_channel(ctx) and not admin_service.is_user_blacklisted(ctx):
                    if len(args) == 0:
                        await schedule.get(ctx)
                    elif len(args) == 1:
                        # Check if correct_format
                        result, hour = await schedule.check_hour_format(args[0])
                        if result is True:
                            await schedule.get(ctx, by_hour=True, hour=hour)
                        else:
                            await ctx.message.add_reaction("❌")
            else:
                await ctx.send('Guild or bot owner please run \'+admin init\' command')
        else:
            if len(args) == 0:
                await schedule.get(ctx)
            elif len(args) == 1:
                # Check if correct_format
                result, hour = await schedule.check_hour_format(args[0])
                if result is True:
                    await schedule.get(ctx, by_hour=True, hour=hour)
                else:
                    await ctx.message.add_reaction("❌")


@bot.command(aliases=['schedule', 's'])
async def get_schedule(ctx, *args):
    if admin_service.files_loaded is True:
        if not (ctx.guild is None and isinstance(ctx.channel, discord.channel.DMChannel)):
            if admin_service.if_guild_init(ctx.guild.id):
                if admin_service.if_registered_channel(ctx) and not admin_service.is_user_blacklisted(ctx):
                    if len(args) == 1 and args[0] == 'all':
                        await schedule.get_full(ctx)
                    elif len(args) > 0:
                        await schedule.get(ctx, filter_schedule=True, args=args)
            else:
                await ctx.send('Guild or bot owner please run \'+admin init\' command')
        else:
            if len(args) == 1 and args[0] == 'all':
                await schedule.get_full(ctx)
            elif len(args) > 0:
                await schedule.get(ctx, filter_schedule=True, args=args)


@bot.command(name='help')
async def help(ctx, *args):
    if admin_service.files_loaded is True:
        is_admin = ctx.author.id == bot_owner or ctx.author.id == ctx.guild.owner_id or await admin_service.is_guild_admin(
            ctx)
        await help_command.send(ctx, args, is_admin)


bot.run(TOKEN)
