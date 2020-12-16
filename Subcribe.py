import os
import json
import discord
from time import perf_counter
from copy import copy
from datetime import datetime, timedelta
from pathlib import Path
from json import JSONDecodeError


class Subcribe:

    def __init__(self, database_ref, schedule_ref, bot):
        self.ping_role_name = "GDQping"
        self.database = database_ref
        self.schedule = schedule_ref
        self.bot = bot
        self.mute = False

        self.subscriptions = list()

        self.reminder_service_next_runtime = datetime.utcnow() + timedelta(seconds=1)

    async def sub(self, ctx, args, schedule, sub_all=False):
        sch_max_len = len(schedule.data)
        role = discord.utils.get(ctx.guild.roles, name=self.ping_role_name)
        member = ctx.author
        if sub_all is False:
            options = args[0].split(',')
            args_to_process = len(options)
            errors = 0
            runs_to_insert = dict()
            for op in options:
                try:
                    run_id = int(op)
                    if 1 <= run_id <= sch_max_len:
                        guild_id = str(ctx.guild.id)
                        member_id = str(member.id)
                        index = guild_id + member_id + str(run_id)
                        runs_to_insert[index] = {"discord_id": member_id, "guild_id": guild_id, "run_id": run_id,
                                                 "index": index}
                    else:
                        errors = errors + 1
                except ValueError:
                    errors = errors + 1

            result, data = await self.__insert_runs(runs_to_insert)

            if errors < args_to_process:
                await ctx.message.add_reaction('✅')

            if result is True:
                # send updates to database
                await self.database.sub_to_many_games(data)
            else:
                print(f'No updates sent to DB for {ctx.author.name}')
        else:
            # Insert to local data
            guild = str(ctx.guild.id)
            member_id = str(member.id)
            index = guild + member_id + str(0)
            result, data = await self.__insert_runs(
                {index: {"discord_id": member_id, "guild_id": guild, "run_id": 0, "index": index}})

            # Add role to if insert successful
            if result is True:
                if role not in member.roles:
                    await member.add_roles(role)
                await ctx.message.add_reaction('✅')

            # Send data to DB if insert successful
            if result is True:
                # send updates to database
                await self.database.sub_to_many_games(data)
            else:
                print(f'No updates sent to DB for {ctx.author.name}')

    async def unsub(self, ctx, args, schedule, sub_all=False):
        sch_max_len = len(schedule.data)
        role = discord.utils.get(ctx.guild.roles, name=self.ping_role_name)
        member = ctx.author
        if sub_all is False:
            options = args[0].split(',')
            args_to_process = len(options)
            errors = 0
            runs_to_remove = dict()
            for op in options:
                try:
                    run_id = int(op)
                    if 1 <= run_id <= sch_max_len:
                        guild_id = str(ctx.guild.id)
                        member_id = str(member.id)
                        index = guild_id + member_id + str(run_id)
                        runs_to_remove[index] = {"discord_id": member_id, "guild_id": guild_id, "run_id": run_id,
                                                 "index": index}
                    else:
                        errors = errors + 1
                except ValueError:
                    errors = errors + 1

            result, data = await self.__remove_runs(runs_to_remove)

            if errors < args_to_process:
                await ctx.message.add_reaction('✅')

            if result is True:
                # send updates to database
                await self.database.unsub_to_many_games(data)
            else:
                print(f'No updates sent to DB for {ctx.author.name}')
        else:
            # Insert to local data
            guild = str(ctx.guild.id)
            member_id = str(member.id)
            index = guild + member_id + str(0)
            result, data = await self.__remove_runs(
                {index: {"discord_id": member_id, "guild_id": guild, "run_id": 0, "index": index}})

            # Add role to if insert successful
            if result is True:
                if role not in member.roles:
                    await member.remove_roles(role)
                await ctx.message.add_reaction('✅')

            # Send data to DB if insert successful
            if result is True:
                # send updates to database
                await self.database.unsub_to_many_games(data)
            else:
                print(f'No updates sent to DB for {ctx.author.name}')

    async def purge(self, ctx):
        result, data = await self.__purge_runs(ctx.author.id, ctx.guild.id)

        if result is True:
            await ctx.message.add_reaction('✅')
            db_result = await self.database.purge_subs_by_user(ctx.author.id, ctx.guild.id)
            if db_result is False:
                print(f'Error deleting all subs for {ctx.author.name}')
        else:
            await self.database.unsub_to_many_games(data)

    @staticmethod
    async def help(ctx):
        help_text = '```How to subcribe to runs\n'
        help_text = help_text + '--------------------------\n'
        help_text = help_text + 'Subcribe to all runs:' \
                                '\n    +sub all\n'
        help_text = help_text + 'Subcribe to a specific game:' \
                                '\n     +sub [run id]\n'
        help_text = help_text + '\nYou can find the run id by searching the schedule with:' \
                                '\n+schedule name "[name of game]"'
        help_text = help_text + '```'

        await ctx.send(help_text)

    async def load(self):
        await self.__load_from_file()
        print(f'Loaded {len(self.subscriptions)} runs from file')

    async def list_subs(self, ctx):
        sub_list = await self.__get_user_subs_by_id(ctx.author.id, ctx.guild.id, limit=10)
        list_text = f'```md\n{ctx.author.name}\'s Subscriptions\n'
        list_text = list_text + '-----------------------------------\n'
        if sub_list is None or len(sub_list) == 0:
            list_text = list_text + 'You are not subscribed to anything.\n```'
            await ctx.send(list_text)
            return
        else:
            all_sub_line = None
            single_sub_title = '\n\nThese games are coming up:\n-----------------------------------\n'
            single_sub_chunk = list()
            for sub in sub_list:
                if sub_list[sub]['run_id'] == 0:
                    all_sub_line = '❗ - Following all runs: You will get a notification for every run.'
                else:
                    name, time_left = await self.__get_run_from_id(sub_list[sub]['run_id'])
                    single_sub_chunk.append(f'{sub_list[sub]["run_id"]}. {name} [{time_left}]')

            if all_sub_line is None:
                list_text = list_text + f'❕ - Following only subscribed runs: You will only get a notifications to ' \
                                        f'runs you are subscribed to (Please look below to see the games you ' \
                                        f'are following.)'
            else:
                list_text = list_text + all_sub_line

            if len(single_sub_chunk) == 0:
                list_text = list_text + single_sub_title + '(None)'
            else:
                list_text = list_text + single_sub_title + '\n'.join(single_sub_chunk)
            t3 = perf_counter()
            await ctx.send(list_text + '```')
            t4 = perf_counter()
            print(f'Execute time for sub list ctx.send: {(t4 - t3) * 1000:0.4f}ms')

    async def is_time_to_run_service(self):
        if datetime.utcnow() > self.reminder_service_next_runtime:
            return True
        else:
            return False

    # Looping service
    async def reminder_service(self, guild_information):

        # Checks if any reminders are ready to be sent
        for run in self.schedule.data:
            run_datetime = (self.schedule.service.strtodatetime(run["time"])) - timedelta(minutes=10)
            end_of_run = (run_datetime + timedelta(minutes=(run["length"] + 10)))
            if run_datetime < datetime.utcnow() < end_of_run and run["reminded"] is False:
                # set reminded
                run["reminded"] = True
                # await self.schedule.save()
                # await self.database.update_schedule_remind(run)


                await self.__validate_roles(run["run_id"], guild_information)

                # Build embed for reminder message
                reminder_embed = discord.Embed(title="GAMES DONE QUICK 2020",
                                               url="https://gamesdonequick.com/schedule", color=0x466e9c)
                reminder_embed.set_thumbnail(url="https://gamesdonequick.com/static/res/img/gdqlogo.png")
                reminder_embed.set_footer(text='Speedrun start times are subject to change')
                reminder_embed.add_field(
                    name=f'Coming up next:',
                    value=f'{run["game"]} ({run["run"]})\nBy: {run["runners"]} | '
                          f'Estimated length: {self.schedule.service.explode_minutes(run["length"])}',
                    inline=False)

                # Get channels reminder will be sent to
                channel_list = list()

                for guild in guild_information:
                    for ch in guild_information[guild]['channels']:
                        channel_list.append(ch)
                print(channel_list)
                # Send embed message to all channels
                for channel in channel_list:
                    channel_to_send_to = await self.bot.fetch_channel(channel)
                    print(channel_to_send_to)
                    if channel_to_send_to is not None:
                        role = discord.utils.get(channel_to_send_to.guild.roles, name=self.ping_role_name)
                        message_content = ""
                        if role is not None:
                            if self.mute is False:
                                message_content = role.mention
                            else:
                                message_content = ''
                        else:
                            raise ValueError(f'Unable to get \'{self.ping_role_name}\' role '
                                             f'from \'{channel_to_send_to.guild.name}\' guild')
                        message_content = \
                            message_content + f" \"{run['game']}\" is starting Soon " \
                                              f"- https://www.twitch.tv/gamesdonequick"
                        await channel_to_send_to.send(message_content, embed=reminder_embed)

                break
            elif datetime.utcnow() > end_of_run and run["reminded"] is False:
                run["reminded"] = True
                # await self.schedule.save()
                # await self.database.update_schedule_remind(run)

        await self.__next_runtime()

    async def __validate_roles(self, run_id, guild_information):
        for guild in guild_information:
            guild_id = guild_information[guild]['guild_id']
            # subs = await self.database.get_subs_by_guild(run_id, guild_id)
            subs = await self.__get_subs_by_guild(run_id, guild_id)
            print(f'Subs: {subs}')
            # Get Guild reference
            guild = await self.bot.fetch_guild(guild_id)
            # Get Role
            role = discord.utils.get(guild.roles, name=self.ping_role_name)
            # Give roles to all members part of the sub list
            for sub in subs:
                member = await guild.fetch_member(sub['discord_id'])
                await member.add_roles(role)

            # Get all guild members with the role, refetch guild data so we have latest state of guild
            guild = await self.bot.fetch_guild(guild_id)

            members_with_roles = list()
            members_to_delete = list()

            guild_owner = await guild.fetch_member(guild.owner_id)
            if role in guild_owner.roles:
                members_with_roles.append(guild_owner)
                members_to_delete.append(guild_owner)

            for member in guild.members:
                member = await guild.fetch_member(member.id)
                if role in member.roles:
                    members_with_roles.append(member)
                    members_to_delete.append(member)

            print(members_with_roles)
            # Remove the users that need the role from members_to_delete
            # the leftover users are not supposed to have the role
            for member in members_with_roles:
                if any(m["discord_id"] == str(member.id) for m in subs):
                    members_to_delete.remove(member)

            # Remove roles for leftover members
            for member in members_to_delete:
                await member.remove_roles(role)

            # Remove all subs to previous run when run_id - 1 != 0
            print(f'Pre role validation length: {len(members_with_roles)}')
            guild = await self.bot.fetch_guild(guild_id)

            members_with_roles = list()
            members_to_delete = list()

            guild_owner = await guild.fetch_member(guild.owner_id)
            if role in guild_owner.roles:
                members_with_roles.append(guild_owner)
                members_to_delete.append(guild_owner)

            for member in guild.members:
                member = await guild.fetch_member(member.id)
                if role in member.roles:
                    members_with_roles.append(member)
                    members_to_delete.append(member)

            for member in members_with_roles:
                if not any(sub["discord_id"] == str(member.id) for sub in subs):
                    await member.add_roles(role)

            print(f'Post role validation length: {len(members_with_roles)}')

            del members_with_roles
            del members_to_delete

    async def __get_subs_by_guild(self, r_id, g_id):
        sub_list = {key: self.subscriptions[key] for key in self.subscriptions if
                    self.subscriptions[key]['guild_id'] == str(g_id) and (
                            self.subscriptions[key]['run_id'] == r_id or self.subscriptions[key]['run_id'] == 0)}
        print(f'Pre cleaned subs: {sub_list}')
        # Find duplitcate items and remove them, run 0 take priority
        cleaned_list = list()
        for key in sub_list:
            if sub_list[key]["run_id"] == 0:
                cleaned_list.append(sub_list[key])
            elif sub_list[key]["run_id"] == r_id:
                if not any(
                        sub_list[s]["discord_id"] == sub_list[key]["discord_id"] and sub_list[s]["run_id"] == 0 for s in
                        sub_list):
                    cleaned_list.append(sub_list[key])

        return cleaned_list

    async def __next_runtime(self):
        self.reminder_service_next_runtime = datetime.utcnow() + timedelta(seconds=15)

    async def __get_run_from_id(self, run_id):
        run = discord.utils.find(lambda r: r['run_id'] == run_id and r['reminded'] is False, self.schedule.data)
        run_time = self.schedule.service.strtodatetime(run['time'])
        hours, minutes, seconds = self.schedule.service.diff_dates(datetime.utcnow(), run_time)
        time_left = f'{hours + minutes}'
        return run['game'], time_left

    async def __get_user_subs_by_id(self, u_id, g_id, limit=151):
        if limit > 50:
            limit = 50

        count = 0
        sub_dict = dict()

        for (key, value) in self.subscriptions.items():
            if self.subscriptions[key]['guild_id'] == str(g_id) and self.subscriptions[key]['discord_id'] == str(u_id) \
                    and count <= limit:
                sub_dict[key] = value
                count = count + 1
            elif count > limit:
                break

        return sub_dict

    async def __insert_runs(self, list_of_runs):
        runs_inserted = dict()
        for run in list_of_runs:
            if run not in self.subscriptions:
                self.subscriptions[run] = list_of_runs[run]
                runs_inserted[run] = list_of_runs[run]

        # Validate insertions
        for run in runs_inserted:
            if run not in self.subscriptions:
                print(f'ERROR: Index \'{run}\' was not inserted due to error')
                del runs_inserted[run]

        if len(runs_inserted) == 0:
            return False, None
        else:
            await self.__save_runs_to_file()
            return True, runs_inserted

    async def __remove_runs(self, list_of_runs):
        runs_deleted = dict()
        for run in list_of_runs:
            if run in self.subscriptions:
                runs_deleted[run] = list_of_runs[run]
                del self.subscriptions[run]

        # Validate insertions
        for run in runs_deleted:
            if run in self.subscriptions:
                print(f'ERROR: Index \'{run}\' was not deleted due to error')
                del runs_deleted[run]

        if len(runs_deleted) == 0:
            return False, None
        else:
            await self.__save_runs_to_file()
            return True, runs_deleted

    async def __purge_runs(self, u_id, g_id):
        runs_to_delete = {key: self.subscriptions[key] for key in self.subscriptions.items()
                          if self.subscriptions[key]['guild_id'] == str(g_id) and
                          self.subscriptions[key]['discord_id'] == str(u_id)}

        items_deleted = 0
        # Delete runs from local memory
        for run in runs_to_delete:
            del self.subscriptions[run]
            if run not in self.subscriptions:
                items_deleted = items_deleted + 1

        if len(runs_to_delete) == items_deleted:
            return True, runs_to_delete
        else:
            return False, runs_to_delete

    async def __save_runs_to_file(self):
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data/subscriptions.json')
            data_file = Path(file)
            with open(data_file, 'w') as f:
                f.write(json.dumps(self.subscriptions, indent=4))
                f.close()
                return True
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            now = datetime.utcnow()
            date_string = now.strftime("%m_%d_%Y_%H_%M_%S")
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, f'data/subscriptions_dump_{date_string}.txt')
            data_file = Path(file)
            with open(data_file, 'w') as f:
                print(self.subscriptions, file=f)
                print(f'Error saving file, dumped to /subscriptions_dump_{date_string}.txt')
                f.close()
            return False

    async def __load_from_file(self):
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data/subscriptions.json')
            session_data_file = Path(file)
            with open(session_data_file, 'r') as f:
                data = json.load(f)
                f.close()
                self.subscriptions = data
                return True
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            return False
