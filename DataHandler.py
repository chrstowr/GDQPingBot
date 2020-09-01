import os
import json
import urllib.request

import discord
from pathlib import Path
from json import JSONDecodeError
from datetime import datetime, timedelta
from bs4 import BeautifulSoup


class DataHandler:
    def __init__(self):
        self.user_list = {}
        self.schedule = list()
        self.ping_role_name = "GDQping"
        self.delay = 0

    async def add_user(self, user, ctx):
        role = discord.utils.get(ctx.guild.roles, name=self.ping_role_name)
        member = discord.utils.get(ctx.guild.members, id=user.id)
        if role not in member.roles:
            # self.user_list[str(user.id)] = {}
            # self.save_to_file()
            await member.add_roles(role)
            print(f'{user} has been added to the GDQ ping list')
            return True

    async def remove_user(self, user, ctx):
        role = discord.utils.get(ctx.guild.roles, name=self.ping_role_name)
        member = discord.utils.get(ctx.guild.members, id=user.id)
        if role in member.roles:
            # self.user_list.pop(str(user.id))
            await member.remove_roles(role)
            print(f'{user} has been removed the GDQ ping list')
            return True

    async def get_schedule(self, ctx):
        limit = 4
        limit_tracker = 1

        # Prevent out of bounds error
        if len(self.schedule) < 4:
            limit = len(self.schedule)

        schedule_embed = discord.Embed(title="GAMES DONE QUICK 2020 - Coming up",
                                       url="https://gamesdonequick.com/schedule",
                                       description="--Please click title for full schedule\n", color=0x466e9c)
        schedule_embed.set_thumbnail(url="https://gamesdonequick.com/static/res/img/gdqlogo.png")
        schedule_embed.set_footer(text='*Speedrun start times are subject to change*')

        for run in self.schedule:
            run_time = self.strtodatetime(run["time"])
            reminder_time = run_time - timedelta(minutes=5)
            end_time = run_time + timedelta(minutes=run["length"])
            # print(f'{datetime.utcnow()} <= {reminder_time}')
            if (datetime.utcnow() < reminder_time or (
                    reminder_time < datetime.utcnow() < end_time)) and limit_tracker <= limit:
                # print('Match')
                # print(run["game"])
                if limit_tracker == 1:
                    if datetime.utcnow() > run_time:
                        schedule_embed.add_field(
                            name=f'Playing now: {run["game"]} ({run["run"]})',
                            value=f'By: {run["runners"]} | '
                                  f'Estimated length: {self.explodeminutes(run["length"])}',
                            inline=False)
                    else:
                        time_remaining = self.diffdates(datetime.utcnow(), run_time)
                        schedule_embed.add_field(
                            name=f'{run["game"]} ({run["run"]}) in {time_remaining}',
                            value=f'By: {run["runners"]} | '
                                  f'Estimated length: {self.explodeminutes(run["length"])}',
                            inline=False)
                else:
                    time_remaining = self.diffdates(datetime.utcnow(), run_time)
                    schedule_embed.add_field(
                        name=f'{run["game"]} ({run["run"]}) in {time_remaining}',
                        value=f'By: {run["runners"]} | '
                              f'Estimated length: {self.explodeminutes(run["length"])}',
                        inline=False)
                limit_tracker = limit_tracker + 1

        await ctx.send(content="https://www.twitch.tv/gamesdonequick", embed=schedule_embed)

    @staticmethod
    def strtodatetime(datetime_str):
        if isinstance(datetime_str, datetime):
            datetime_str = datetime_str.strftime("%Y-%m-%d %H:%M:%S")

        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

    @staticmethod
    def diffdates(now, later):
        diff = later - now
        hours = divmod(diff.total_seconds(), 3600)[0]
        minutes = divmod(diff.total_seconds(), 60)[0] - (hours * 60)
        seconds = diff.total_seconds() - (hours * 3600) - (minutes * 60)
        return f'{hours:.0f}h {round(minutes):.0f}m {seconds:.0f}s'

    @staticmethod
    def explodeminutes(minutes):
        hours = int(minutes / 60)
        minutes = minutes - (hours * 60)

        return f'{hours}h {minutes}m'

    async def load_schedule(self):
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'gdq2020schedule.json')
            session_data_file = Path(file)
            with open(session_data_file, 'r') as f:
                data = json.load(f)
                f.close()
                self.schedule = data
                return True
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            return False

    async def save_schedule(self):

        def json_filter(o):
            if isinstance(o, datetime):
                return o.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return o

        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'gdq2020schedule.json')
            data_file = Path(file)
            with open(data_file, 'w') as f:
                f.write(json.dumps(self.schedule, indent=4, default=json_filter))
                f.close()
                return True
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            return False

    @staticmethod
    async def get_delay_delta():
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'delay.json')
            session_data_file = Path(file)
            with open(session_data_file, 'r') as f:
                data = json.load(f)
                f.close()
                hours = divmod(data[0], 60)[0]
                minutes = data[0] - (hours * 60)
                delay_delta = timedelta(hours=hours, minutes=minutes)
                return delay_delta
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            return None

    async def get_refresh_datetime(self):
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'schedule_refresh.json')
            session_data_file = Path(file)
            with open(session_data_file, 'r') as f:
                data = json.load(f)
                f.close()
                return self.strtodatetime(data[0])
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            return None

    @staticmethod
    def save_refresh_datetime(new_dt):

        def datetime_format(o):
            if isinstance(o, datetime):
                return o.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return o

        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'schedule_refresh.json')
            data_file = Path(file)
            with open(data_file, 'w') as f:
                f.write(json.dumps([new_dt], indent=4, default=datetime_format))
                f.close()
                return True
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            return False

    def reload_schedule(self):
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
        for run in data:
            if len(run) == 7:
                run_dict = {}
                time = datetime.strptime(run[0], "%Y-%m-%dT%H:%M:%SZ")
                length_text = run[4].split(':')
                length = (int(length_text[0]) * 60) + int(length_text[1])

                run_dict = {
                    "time": time,
                    "length": length,
                    "game": run[1],
                    "run": run[5],
                    "runners": run[2],
                    "host": run[6],
                    "reminded": False
                }
                master_schedule.append(run_dict)
            elif len(run) == 4:
                time = datetime.strptime(run[0], "%Y-%m-%dT%H:%M:%SZ")
                length_text = run[3].split(':')
                length = (int(length_text[0]) * 60) + int(length_text[1])
                run_dict = {
                    "time": time,
                    "length": length,
                    "game": run[1],
                    "run": "",
                    "runners": run[2],
                    "host": "",
                    "reminded": False
                }
                master_schedule.append(run_dict)

        def json_filter(o):
            if isinstance(o, datetime):
                return o.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return o

        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'schedule-bak.json')
            data_file = Path(file)
            with open(data_file, 'w') as f:
                f.write(json.dumps(master_schedule, indent=4, default=json_filter))
                f.close()
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')

        # Cross check with schedule in memory
        time_updates = 0
        for run in master_schedule:
            match = discord.utils.find(lambda r: r["game"] == run["game"], self.schedule)
            if match is not None:

                if match["time"] != run["time"]:
                    time_updates = time_updates + 1

                match["length"] = run["length"]
                match["time"] = run["time"]

        return f'Total updates: {time_updates} '
