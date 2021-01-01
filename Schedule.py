from ScheduleServices import ScheduleServices
import os
import json
import urllib.request
import re
import discord
import math
from pathlib import Path
from json import JSONDecodeError
from datetime import datetime, timedelta
from bs4 import BeautifulSoup


# TODO: Add timestamps to log outputs

class Schedule:
    def __init__(self, database_ref):
        self.data = list()
        self.delay = 0
        self.database = database_ref
        self.service = ScheduleServices()
        self.multi_page_schedule_sessions = dict()
        self.multi_page_schedule_cleanup_next_runtime = datetime.utcnow() + timedelta(seconds=10)

        self.accepted_filter_options = ['name', 'runner', 'host']

    async def raw_data(self):
        return self.data

    # Helper for get()
    @staticmethod
    def __iterator_item_matches(item, search_term):
        r = re.search("\\b" + search_term.lower() + "\\b", item['game'].lower())
        if r is None:
            return False
        else:
            return True

        # Helper for get()

    @staticmethod
    def __iterator_item_matches_to_string(item, search_term):
        r1 = re.search("\\b" + search_term.lower() + "\\b", item['game'].lower())
        r2 = re.search("\\b" + search_term.lower() + "\\b", item['runners'].lower())
        r3 = re.search("\\b" + search_term.lower() + "\\b", item['host'].lower())
        if any(reg is not None for reg in [r1, r2, r3]):
            return True
        else:
            return False

    # Helper for get()
    async def __apply_filter(self, args, data_iterator):
        error = False
        error_text = ""
        for option in self.accepted_filter_options:
            if option in args:
                option_index = args.index(option)
                try:
                    search_term = args[option_index + 1]
                    new_data_iterator = [d for d in data_iterator if self.__iterator_item_matches(d, search_term)]
                    return new_data_iterator, error, error_text, search_term
                except IndexError:
                    error_text = f'Value for\'{option}\' is missing. ' \
                                 f'Proper format: [name, runner, host] \"[search value]\"'
                    error = True
        return data_iterator, error, error_text, None

        # Helper for get()

    async def __apply_filter_from_string(self, args, data_iterator):
        error = False
        error_text = ""

        search_string = args[0]
        new_data_iterator = [d for d in data_iterator if self.__iterator_item_matches_to_string(d, search_string)]
        return new_data_iterator, error, error_text, search_string

    # TODO: Set option to DM whole schedule
    async def get(self, ctx, filter_schedule=False, args=None):
        limit = 4
        limit_tracker = 1
        data_iterator = self.data
        filter_applied = ""

        print(f'{ctx.author.name} | get schedule | {datetime.utcnow()}')

        # Apply Filters if needed
        if filter_schedule is True and len(args) > 1:
            if any(o in args for o in self.accepted_filter_options):
                result_iterator, error, error_text, filter_applied = await self.__apply_filter(args, data_iterator)
                if error is False:
                    data_iterator = result_iterator
                else:
                    await ctx.send(f'Error: {error_text}')
                    return
            else:
                filter_schedule = False
        elif filter_schedule is True and len(args) == 1:
            result_iterator, error, error_text, filter_applied = await self.__apply_filter_from_string(args,
                                                                                                       data_iterator)
            if error is False:
                data_iterator = result_iterator
            else:
                await ctx.send(f'Error: {error_text}')
                return

        title_desc = "Here are the upcoming games: \n"
        if filter_schedule is True:
            curr_page = 1
            max_page = math.ceil(len(data_iterator) / limit)
            title_desc = f"Here are the results for \"{filter_applied}\" - Page {curr_page}/{max_page}\n"
        schedule_embed = discord.Embed(title="GAMES DONE QUICK 2020 - Click me for full schedule",
                                       url="https://gamesdonequick.com/schedule",
                                       description=title_desc, color=0x466e9c)
        schedule_embed.set_thumbnail(url="https://gamesdonequick.com/static/res/img/gdqlogo.png")

        if filter_schedule is True:
            if len(data_iterator) > limit:
                schedule_embed.set_footer(
                    text=f'*Speedrun start times are subject to change* | {len(data_iterator)} result(s) found | '
                         f'Results 1-4 out of {len(data_iterator)} \n| Session Expires in 60s')
            else:
                schedule_embed.set_footer(
                    text=f'*Speedrun start times are subject to change* | {len(data_iterator)} result(s) found')
        else:
            schedule_embed.set_footer(text='*Speedrun start times are subject to change*')

        for run in data_iterator:
            run_time = self.service.strtodatetime(run["time"])
            reminder_time = run_time - timedelta(minutes=10)
            end_time = run_time + timedelta(minutes=run["length"])

            before_reminder_time = datetime.utcnow() < reminder_time
            between_reminder_time_and_end_of_run = reminder_time < datetime.utcnow() < end_time
            if (before_reminder_time or between_reminder_time_and_end_of_run) and limit_tracker <= limit:
                if limit_tracker == 1 and datetime.utcnow() > run_time:
                    schedule_embed.add_field(
                        name=f'Playing now: {run["game"]} ({run["run"]})',
                        value=f'By: {run["runners"]} | '
                              f'Estimated length: {self.service.explode_minutes(run["length"])}\n',
                        inline=False)
                else:
                    hours, minutes, seconds = self.service.diff_dates(datetime.utcnow(), run_time)
                    schedule_embed.add_field(
                        name=f'{run["run_id"]}--{run["game"]} ({run["run"]}) in {hours + minutes}',
                        value=f'By: {run["runners"]} | '
                              f'Estimated length: {self.service.explode_minutes(run["length"])}',
                        inline=False)
                limit_tracker = limit_tracker + 1

        if len(data_iterator) == 0 and filter_schedule is True:
            schedule_embed.add_field(
                name=f'No results found for \"{filter_applied}\"',
                value="Please let the developer know if this is a mistake and check the official schedule.",
                inline=False)
        else:
            while limit_tracker <= limit:
                self.__add_empty_embed_line(schedule_embed)
                limit_tracker = limit_tracker + 1

        message_context = await ctx.send(content="https://www.twitch.tv/gamesdonequick", embed=schedule_embed)

        if len(data_iterator) > limit and filter_schedule is True:
            g_id = str(message_context.guild.id)
            m_id = str(message_context.id)

            if g_id not in self.multi_page_schedule_sessions:
                self.multi_page_schedule_sessions[g_id] = dict()

            self.multi_page_schedule_sessions[g_id][m_id] = MultiPageScheduleModel(message_context, data_iterator,
                                                                                   filter_applied, limit, self.service)
            await self.multi_page_schedule_sessions[g_id][m_id].add_controls()

    # main() reaction listener
    async def multi_page_schedule_reaction_listener(self, reaction, user):
        m_id = str(reaction.message.id)
        g_id = str(reaction.message.guild.id)
        session = self.multi_page_schedule_sessions[g_id][m_id]

        if reaction.emoji == "⬆":
            await session.prev_page(reaction, user)
        elif reaction.emoji == "⬇":
            await session.next_page(reaction, user)
        else:
            await reaction.remove(user)

    async def is_multi_page_session(self, reaction):
        m_id = str(reaction.message.id)
        g_id = str(reaction.message.guild.id)

        if g_id in self.multi_page_schedule_sessions and m_id in self.multi_page_schedule_sessions[g_id]:
            return True
        else:
            return False

    # Looping service
    async def schedule_update_service(self, subscription, schedule_refresh_rate=5):
        # print(f'Syncing local schedule with online schedule: {datetime.utcnow()}')
        # Sync local schedule with latest schedule
        old_schedule = self.data.copy()
        await self.dev_sync(subscription)
        new_schedule = self.data.copy()
        await self.__schedule_comp(old_schedule, new_schedule)
        new_refresh_datetime = datetime.utcnow() + timedelta(minutes=schedule_refresh_rate)
        self.service.save_refresh_datetime(new_refresh_datetime)

    @staticmethod
    async def __schedule_comp(old, new):
        time_updates = 0
        added_runs = len(new) - len(old)

        for item in old:
            for item2 in new:
                if item2['game'] == item['game']:
                    if item2['time'] != item['time']:
                        time_updates = time_updates + 1
                    break

        if time_updates > 0 or added_runs != 0:
            print(
                f'Updates from latest sync: Time updates: {time_updates} | Added runs: {added_runs} | '
                f'{datetime.utcnow()}')

    async def is_time_to_run_schedule_sync_service(self):
        refresh_datetime = await self.service.get_refresh_datetime()
        if datetime.utcnow() > refresh_datetime:
            return True
        else:
            return False

    async def is_time_to_run_cleanup_service(self):
        past_runtime = datetime.utcnow() > self.multi_page_schedule_cleanup_next_runtime
        if past_runtime and len(self.multi_page_schedule_sessions):
            return True
        else:
            return False

    async def __next_runtime(self):
        self.multi_page_schedule_cleanup_next_runtime = datetime.utcnow() + timedelta(seconds=10)

    # Looping service
    async def multi_page_schedule_cleanup_service(self):
        if len(self.multi_page_schedule_sessions) > 0:
            cleaned_up_session = 0

            # New implementation of clearing multipage sessions
            for guild, guild_sessions in self.multi_page_schedule_sessions.copy().items():
                for session_id, session in guild_sessions.copy().items():
                    if session.is_expired():
                        await session.remove_controls()
                        del self.multi_page_schedule_sessions[guild][session_id]
                        cleaned_up_session = cleaned_up_session + 1

            await self.__next_runtime()

            # Update all sessions
            for guild, guild_sessions in self.multi_page_schedule_sessions.copy().items():
                for session_id, session in guild_sessions.copy().items():
                    await session.update()

    async def get_run_from_id(self, req_id):
        found_run = [r for r in self.data.copy() if r['run_id'] == req_id][0]

        if found_run is not None and found_run["reminded"] is not True:
            return found_run
        else:
            return None

    async def load(self, subscription):
        # self.data = await self.database.load_schedule()
        await self.__load_from_file()
        if len(self.data) > 0:
            return True, len(self.data)
        else:
            await self.dev_sync(subscription)
            if len(self.data) == 0:
                return False, 0
            else:
                await self.__save_to_file()
                return True, len(self.data)

    async def save(self):

        def json_filter(o):
            if isinstance(o, datetime):
                return o.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return o

        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data/schedule_data.json')
            data_file = Path(file)
            with open(data_file, 'w') as f:
                f.write(json.dumps(self.data, indent=4, default=json_filter))
                f.close()
                return True
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            return False

    async def dev_sync(self, subscription):
        new_schedule = None
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data/gdq2020schedule.json')
            session_data_file = Path(file)
            with open(session_data_file, 'r') as f:
                data = json.load(f)
                f.close()
                new_schedule = data
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')

        r_id = 1
        for run in new_schedule:
            # add ids
            run['run_id'] = r_id
            r_id = r_id + 1

            # Convert start times to datetime obj
            run['time'] = datetime.strptime(run['time'], "%Y-%m-%d %H:%M:%S")

            # Check if current time is after reminder time (10 minutes before run start)
            # if yes reminded = True
            if datetime.utcnow() > run['time'] - timedelta(minutes=10):
                run['reminded'] = True

        # Validate run ids are the same
        run_ids_that_changed = list()
        for run in self.data.copy():
            for run2 in new_schedule:
                if run['game'] == run2['game'] and run['run_id'] != run2['run_id']:
                    run_ids_that_changed.append([run['run_id'], run2['run_id']])

        # If there were any mismatches, correct subscriptions
        if len(run_ids_that_changed) > 0:
            await subscription.correct_sub_run_ids(run_ids_that_changed)

        self.data = new_schedule
        await self.__save_to_file()

    async def sync(self, subscription):
        url = "https://gamesdonequick.com/schedule"
        req = urllib.request.Request(url, headers={'User-Agent': "Magic Browser"})
        con = urllib.request.urlopen(req)
        soup = BeautifulSoup(con, 'html.parser')

        data = []
        table = soup.find('table')
        t_body = table.find('tbody')
        rows = t_body.find_all('tr')

        row_pointer = 0
        num_of_rows = len(rows)
        while row_pointer < num_of_rows:
            run_data = list()
            if row_pointer < num_of_rows - 1:
                cols = rows[row_pointer].find_all('td')
                cols = [ele.text.strip() for ele in cols]
                # run_data.append([ele for ele in cols if ele])  # Get rid of empty values
                for ele in cols:
                    if ele:
                        run_data.append(ele)
            row_pointer = row_pointer + 1
            if row_pointer < num_of_rows - 1:
                cols = rows[row_pointer].find_all('td')
                cols = [ele.text.strip() for ele in cols]
                # run_data.append([ele for ele in cols if ele])  # Get rid of empty values
                for ele in cols:
                    if ele:
                        run_data.append(ele)
            row_pointer = row_pointer + 1

            data.append(run_data)

        # Format data
        # 4 - length
        master_schedule = list()
        run_id = 1
        for run in data:
            if len(run) == 7:
                time = datetime.strptime(run[0], "%Y-%m-%dT%H:%M:%SZ")
                length_text = run[4].split(':')
                length = (int(length_text[0]) * 60) + int(length_text[1])
                reminded = False

                if datetime.utcnow() > time - timedelta(minutes=10):
                    reminded = True

                run_dict = {
                    "run_id": run_id,
                    "time": time,
                    "length": length,
                    "game": run[1],
                    "run": run[5],
                    "runners": run[2],
                    "host": run[6],
                    "reminded": reminded
                }
                master_schedule.append(run_dict)
            elif len(run) == 4:
                time = datetime.strptime(run[0], "%Y-%m-%dT%H:%M:%SZ")
                length_text = run[3].split(':')
                length = (int(length_text[0]) * 60) + int(length_text[1])
                reminded = False
                if datetime.utcnow() > time - timedelta(minutes=10):
                    reminded = True

                run_dict = {
                    "run_id": run_id,
                    "time": time,
                    "length": length,
                    "game": run[1],
                    "run": "",
                    "runners": run[2],
                    "host": "",
                    "reminded": reminded
                }
                master_schedule.append(run_dict)
            run_id = run_id + 1

        # Validate run ids are the same
        run_ids_that_changed = list()
        for run in self.data.copy():
            for run2 in master_schedule:
                if run['game'] == run2['game'] and run['run_id'] != run2['run_id']:
                    run_ids_that_changed.append([run['run_id'], run2['run_id']])

        # If there were any mismatches, correct subscriptions
        if len(run_ids_that_changed) > 0:
            await subscription.correct_sub_run_ids(run_ids_that_changed)

        self.data = master_schedule
        await self.__save_to_file()

    async def __save_to_file(self):
        def json_filter(o):
            if isinstance(o, datetime):
                return o.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return o

        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data/schedule_data.json')
            data_file = Path(file)
            with open(data_file, 'w') as f:
                f.write(json.dumps(self.data, indent=4, default=json_filter))
                f.close()
                return True
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            now = datetime.utcnow()
            date_string = now.strftime("%m_%d_%Y_%H_%M_%S")
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, f'data/schedule_dump_{date_string}.txt')
            data_file = Path(file)
            with open(data_file, 'w') as f:
                print(self.data, file=f)
                print(f'Error saving file, dumped to /schedule_dump_{date_string}.txt')
                f.close()
            return False

    async def __load_from_file(self):
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data/schedule_data.json')
            session_data_file = Path(file)
            with open(session_data_file, 'r') as f:
                data = json.load(f)
                f.close()
                self.data = data
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')

    # Helper for get()
    @staticmethod
    def __add_empty_embed_line(schedule_embed):
        schedule_embed.add_field(name='\u200b\n\u200b', value='\u200b', inline=False)

    # DEV FUNCTIONS
    # -----------------------------------------------------------------------------------------------

    async def generate_fake_schedule(self, subscription):
        new_date = datetime.utcnow() + timedelta(minutes=11)

        new_fake_schedule = None
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data/schedule_backup.json')
            session_data_file = Path(file)
            with open(session_data_file, 'r') as f:
                new_fake_schedule = json.load(f)
                # convert datetime strings to objects
                for item in new_fake_schedule:
                    item["time"] = self.service.strtodatetime(item["time"])
                f.close()
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')

        schedule_timedeltas = list()
        prev_time = None
        for item in new_fake_schedule:
            if item['run_id'] == 1:
                prev_time = item['time']
            else:
                time_delta = item['time'] - prev_time
                schedule_timedeltas.append(time_delta)
                prev_time = item['time']

        # Iterate through fake schedule, set new start datetime on first run, then iterate it
        #  using previously generated timedelta list
        prev_time = None
        delta_list_index = 0
        for item in new_fake_schedule:
            if item['run_id'] == 1:
                new_start_date = self.service.strtodatetime(new_date)
                item['time'] = new_start_date
                prev_time = item['time']
            else:
                item['time'] = prev_time + schedule_timedeltas[delta_list_index]
                prev_time = item['time']
                delta_list_index = delta_list_index + 1

        def json_filter(o):
            if isinstance(o, datetime):
                return o.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return o

        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data/gdq2020schedule.json')
            data_file = Path(file)
            with open(data_file, 'w') as f:
                f.write(json.dumps(new_fake_schedule, indent=4, default=json_filter))
                f.close()
                await self.sync(subscription)
                return True, f"New schedule generation success! New start datetime: {new_date}"
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            now = datetime.utcnow()
            date_string = now.strftime("%m_%d_%Y_%H_%M_%S")
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, f'data/fake_schedule_dump_{date_string}.txt')
            data_file = Path(file)
            with open(data_file, 'w') as f:
                print(new_fake_schedule, file=f)
                print(f'Error saving file, dumped to /fake_schedule_dump_{date_string}.txt')
                f.close()
            return False, "Error saving new schedule due to JSONDecode Error"

    async def delay_schedule(self, hours=0, minutes=0):
        pass


class MultiPageScheduleModel:
    def __init__(self, ctx, data_iterator, filter_applied, limit, service, expire_seconds=60):
        # self.guild_id = ctx.guild.id
        # self.message = ctx.id
        self.ctx = ctx
        self.data = data_iterator
        self.filter_string = filter_applied
        self.limit = limit
        self.service = service
        self.num_of_results = len(data_iterator)
        self.data_pages = list()
        self.current_page = 0
        self.expires = datetime.utcnow() + timedelta(seconds=expire_seconds)

        # Find data subdivisions
        base_value = 0
        end_value = limit

        # Create page range list
        while True:
            self.data_pages.append([base_value, end_value])

            base_value = base_value + limit
            end_value = end_value + limit

            if end_value > self.num_of_results:
                end_value = self.num_of_results

            if base_value > self.num_of_results:
                break

    async def add_controls(self):
        # print('adding controls')
        await self.ctx.add_reaction("⬆")
        await self.ctx.add_reaction("⬇")

    async def remove_controls(self):
        message = await self.ctx.channel.fetch_message(self.ctx.id)
        await message.edit(embed=await self.get_embed())
        for react in message.reactions:
            await react.clear()

    async def next_page(self, reaction, user):
        data_page_max_index = len(self.data_pages) - 1
        if self.current_page < data_page_max_index:
            self.current_page = self.current_page + 1
            schedule_embed = await self.get_embed()
            await self.ctx.edit(embed=schedule_embed)
        await reaction.remove(user)

    async def prev_page(self, reaction, user):
        if self.current_page > 0:
            self.current_page = self.current_page - 1
            schedule_embed = await self.get_embed()
            await self.ctx.edit(embed=schedule_embed)
        await reaction.remove(user)

    async def update(self):
        schedule_embed = await self.get_embed()
        await self.ctx.edit(embed=schedule_embed)

    @staticmethod
    def __add_empty_embed_line(schedule_embed):
        schedule_embed.add_field(name='\u200b', value='\u200b', inline=False)

    async def get_embed(self):
        base_page = self.data_pages[self.current_page][0]
        final_page = self.data_pages[self.current_page][1]
        limit_tracker = 1
        curr_page = self.current_page + 1
        max_page = len(self.data_pages)

        title_desc = f"Here are the results for \"{self.filter_string}\" - Page {curr_page}/{max_page}\n"
        schedule_embed = discord.Embed(title="GAMES DONE QUICK 2020 - Click me for full schedule",
                                       url="https://gamesdonequick.com/schedule",
                                       description=title_desc, color=0x466e9c)
        schedule_embed.set_thumbnail(url="https://gamesdonequick.com/static/res/img/gdqlogo.png")
        if not self.is_expired():
            hours, minutes, seconds = self.service.diff_dates(datetime.utcnow(), self.expires)
            expire_text = f'Session Expires in {seconds}'
        else:
            expire_text = f' Session EXPIRED'

        schedule_embed.set_footer(
            text=f'*Speedrun start times are subject to change* | {len(self.data)} result(s) found | '
                 f'Results {base_page + 1} - {final_page} out of {len(self.data)}\n | {expire_text}')

        for run in self.data.copy()[base_page:final_page]:
            run_time = self.service.strtodatetime(run["time"])
            reminder_time = run_time - timedelta(minutes=5)
            end_time = run_time + timedelta(minutes=run["length"])

            before_reminder_time = datetime.utcnow() < reminder_time
            between_reminder_time_and_end_of_run = reminder_time < datetime.utcnow() < end_time
            if (before_reminder_time or between_reminder_time_and_end_of_run) and limit_tracker <= self.limit:
                if limit_tracker == 1 and datetime.utcnow() > run_time:
                    schedule_embed.add_field(
                        name=f'Playing now: {run["game"]} ({run["run"]})',
                        value=f'By: {run["runners"]} | '
                              f'Estimated length: {self.service.explode_minutes(run["length"])}\n',
                        inline=False)
                else:
                    hours, minutes, seconds = self.service.diff_dates(datetime.utcnow(), run_time)
                    schedule_embed.add_field(
                        name=f'{run["run_id"]}--{run["game"]} ({run["run"]}) in {hours + minutes}',
                        value=f'By: {run["runners"]} | '
                              f'Estimated length: {self.service.explode_minutes(run["length"])}',
                        inline=False)
                limit_tracker = limit_tracker + 1

        while limit_tracker <= self.limit:
            self.__add_empty_embed_line(schedule_embed)
            limit_tracker = limit_tracker + 1

        return schedule_embed

    def is_expired(self):
        if datetime.utcnow() > self.expires:
            return True
        else:
            return False
