import json
import os
from datetime import datetime, timedelta
from json import JSONDecodeError
from pathlib import Path

import discord


class Subscribe:

    def __init__(self, database_ref, schedule_ref, bot):
        self.ping_role_name = "GDQping"
        self.database = database_ref
        self.schedule = schedule_ref
        self.bot = bot
        self.mute = False

        self.subscriptions = dict()

        self.reminder_service_next_runtime = datetime.utcnow() + timedelta(seconds=1)

    async def sub(self, ctx, args, schedule, sub_all=False):
        sch_max_len = len(schedule.data)
        role = discord.utils.get(ctx.guild.roles, name=self.ping_role_name)
        member = ctx.author
        print(f'{member.name} | unsub | {args} | {datetime.utcnow()}')
        if sub_all is False:
            options = args[0].split(',')
            args_to_process = len(options)
            errors = 0
            runs_to_insert = dict()
            for op in options:
                try:
                    run_id = int(op)
                    name, time = await self.__get_run_from_id(run_id)
                    if 1 <= run_id <= sch_max_len and name is not None:
                        guild_id = ctx.guild.id
                        member_id = member.id
                        index = str(guild_id) + str(member_id) + str(run_id)
                        runs_to_insert[index] = {"discord_id": member_id, "guild_id": guild_id, "run_id": run_id,
                                                 "index": index}
                    else:
                        errors = errors + 1
                except ValueError:
                    errors = errors + 1

            result, data = await self.__insert_runs(runs_to_insert)

            if errors < args_to_process:
                await ctx.message.add_reaction('✅')
            else:
                await ctx.message.add_reaction('❌')

            if result is True:
                # send updates to database
                await self.database.sub_to_many_games(data)
            else:
                print(f'No updates sent to DB for {ctx.author.name}')
        else:
            # Insert to local data
            guild = ctx.guild.id
            member_id = member.id
            index = str(guild) + str(member_id) + str(0)
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
                        guild_id = ctx.guild.id
                        member_id = member.id
                        index = str(guild_id) + str(member_id) + str(run_id)
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
            guild = ctx.guild.id
            member_id = member.id
            index = str(guild) + str(member_id) + str(0)
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
        print(f'{ctx.author.name} | purge | {datetime.utcnow()}')
        if result is True:
            await ctx.message.add_reaction('✅')
            # db_result = await self.database.purge_subs_by_user(ctx.author.id, ctx.guild.id)
            # if db_result is False:
            #     print(f'Error deleting all subs for {ctx.author.name}')
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
        print(f'Loaded {len(self.subscriptions)} subscriptions from file')

    async def list_subs(self, ctx):
        sub_list = await self.__get_user_subs_by_id(ctx.author.id, ctx.guild.id, limit=10)
        list_text = f'```md\n{ctx.author.name}\'s Subscriptions ({ctx.guild.name})\n'
        list_text = list_text + '-----------------------------------\n'
        if sub_list is None or len(sub_list) == 0:
            list_text = list_text + 'You are not subscribed to anything.\n```'
            await ctx.author.send(list_text)
            return
        else:
            all_sub_line = None
            single_sub_title = '\n\nThese games are coming up:\n-----------------------------------\n'
            single_sub_chunk = list()
            for sub in sub_list:
                if sub['run_id'] == 0:
                    all_sub_line = '❗ - Following all runs: You will get a notification for every run.'
                else:
                    name, time_left = await self.__get_run_from_id(sub['run_id'])
                    if name is not None:
                        single_sub_chunk.append(f'{sub["run_id"]}. {name} [{time_left}]')

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

            await ctx.author.send(list_text + '```')

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
                for key, value in guild_information.items():
                    if value['reminders'] is True:
                        # Get all channels bot is active in
                        channel_list = value['channels']

                        # Pass ID and guild info to validate what roles need to be
                        # fixed
                        await self.__validate_roles(run["run_id"], value)

                        # Build embed for reminder message
                        reminder_embed = discord.Embed(title="GAMES DONE QUICK 2020",
                                                       url="https://gamesdonequick.com/schedule", color=0x466e9c)
                        reminder_embed.set_thumbnail(url="https://gamesdonequick.com/static/res/img/gdqlogo.png")
                        reminder_embed.set_footer(text='Speedrun start times are subject to change')
                        reminder_embed.add_field(
                            name=f'Coming up next:',
                            value=f'{run["run_id"]}-{run["game"]} ({run["run"]})\nBy: {run["runners"]} | '
                                  f'Estimated length: {self.schedule.service.explode_minutes(run["length"])}',
                            inline=False)

                        # Send embed message to all channels for this guild
                        for channel in channel_list:
                            channel_to_send_to = await self.bot.fetch_channel(channel)
                            if channel_to_send_to is not None:
                                role = discord.utils.get(channel_to_send_to.guild.roles, name=self.ping_role_name)
                                message_content = ''
                                if role is not None:
                                    if value['muted'] is False:
                                        message_content = role.mention
                                    message_content = \
                                        message_content + f" \"{run['game']}\" is starting Soon " \
                                                          f"- https://www.twitch.tv/gamesdonequick"
                                    await channel_to_send_to.send(message_content, embed=reminder_embed)
                                else:
                                    await channel_to_send_to.send(f'ERROR: Could not find \'GDQping\' role for guild'
                                                                  f' {channel_to_send_to.guild.name}. Please contact '
                                                                  f'the developer.')
                                    raise ValueError(f'Unable to get \'{self.ping_role_name}\' role '
                                                     f'from \'{channel_to_send_to.guild.name}\' guild')

                # Clean up un-needed sub data
                await self.__delete_old_subs(run['run_id'])
                await self.__save_subs_to_file()
                # Set flag that game reminder has been sent
                run["reminded"] = True
                await self.schedule.save()
                break
            elif datetime.utcnow() > end_of_run and run["reminded"] is False:
                run["reminded"] = True
                await self.schedule.save()

        await self.__next_runtime()

    async def __delete_old_subs(self, run_id):
        for key, value in self.subscriptions.copy().items():
            if value['run_id'] == run_id:
                del self.subscriptions[key]

    async def __validate_roles(self, run_id, guild_info):
        role_addition = True
        role_removal = True

        while role_addition is True or role_removal is True:
            guild_id = guild_info['guild_id']
            subs = await self.__get_subs_by_guild(run_id, guild_id)
            # Get Guild reference
            guild = self.bot.get_guild(guild_id)
            # Get Role
            role = discord.utils.get(guild.roles, name=self.ping_role_name)
            print(f'> Role Validation for {guild.name}, run #{run_id}')
            print(f'{len(subs)} subs for run # {run_id}')
            print(f'{len(role.members)} members with role')

            for sub in subs:
                if not any(r_m.id == sub['discord_id'] for r_m in role.members):
                    member = guild.get_member(sub['discord_id'])
                    await member.add_roles(role)
                    print(f'Add role to {member.name} ({role.guild.name})')
                    role_addition = True
                else:
                    role_addition = False

            for member in role.members:
                if not any(sub['discord_id'] == member.id for sub in subs):
                    await member.remove_roles(role)
                    print(f'Removed role for {member.name} ({role.guild.name})')
                    role_removal = True
                else:
                    role_removal = False

            if len(subs) == 0:
                role_addition = False

            if len(role.members) == 0:
                role_removal = False

    async def __get_subs_by_guild(self, r_id, g_id):
        sub_list = {key: value for key, value in self.subscriptions.copy().items() if
                    value['guild_id'] == g_id and (value['run_id'] == r_id or value['run_id'] == 0)}

        # Find duplitcate items and remove them, run 0 take priority
        cleaned_list = list()
        for key, value in sub_list.copy().items():
            if value["run_id"] == 0:
                cleaned_list.append(value)
            else:
                if not any(
                        value2["discord_id"] == value["discord_id"] and value2["run_id"] == 0
                        for key2, value2 in sub_list.copy().items()):
                    cleaned_list.append(value)

        return cleaned_list

    async def __next_runtime(self):
        self.reminder_service_next_runtime = datetime.utcnow() + timedelta(seconds=15)

    async def __get_run_from_id(self, run_id):
        run = discord.utils.find(lambda r: r['run_id'] == run_id and r['reminded'] is False, self.schedule.data)

        if run is None:
            return None, ""
        else:
            run_time = self.schedule.service.strtodatetime(run['time'])
            hours, minutes, seconds = self.schedule.service.diff_dates(datetime.utcnow(), run_time)
            time_left = f'{hours + minutes}'
            return run['game'], time_left

    async def __get_user_subs_by_id(self, u_id, g_id, limit=50):
        if limit > 50:
            limit = 50

        count = 0
        sub_list = list()

        for (key, value) in self.subscriptions.copy().items():
            if self.subscriptions[key]['guild_id'] == g_id and self.subscriptions[key]['discord_id'] == u_id \
                    and count <= limit:
                sub_list.append(value)
                count = count + 1
            elif count > limit:
                break

        def sort_key(e):
            return e['run_id']

        sub_list.sort(key=sort_key)
        return sub_list

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
            await self.__save_subs_to_file()
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
            await self.__save_subs_to_file()
            return True, runs_deleted

    async def __purge_runs(self, u_id, g_id):
        runs_to_delete = {key: value for key, value in self.subscriptions.copy().items()
                          if value['guild_id'] == g_id and
                          value['discord_id'] == u_id}

        items_deleted = 0
        # Delete runs from local memory
        for run in runs_to_delete:
            del self.subscriptions[run]
            if run not in self.subscriptions:
                items_deleted = items_deleted + 1

        if len(runs_to_delete) == items_deleted:
            await self.__save_subs_to_file()
            return True, runs_to_delete
        else:
            return False, runs_to_delete

    async def correct_sub_run_ids(self, run_ids_that_changed):
        old_sub_dict = self.subscriptions.copy()
        new_sub_dict = dict()

        print(f'Correcting {len(run_ids_that_changed)} subs: {run_ids_that_changed} | {datetime.utcnow()}')

        # Find matching items, if match, pop it and add to new sub dict()
        for r_ids in run_ids_that_changed:
            for key, value in old_sub_dict.copy().items():
                if value['run_id'] == r_ids[0]:
                    value['run_id'] = r_ids[1]
                    new_sub_dict[key] = value
                    del old_sub_dict[key]

        # Add remaining runs
        for key, value in old_sub_dict.items():
            new_sub_dict[key] = value

        self.subscriptions = new_sub_dict
        await self.__save_subs_to_file()

    async def __save_subs_to_file(self):
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
