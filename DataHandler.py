import os
import json
import discord
from pathlib import Path
from json import JSONDecodeError
from datetime import datetime


class DataHandler:
    def __init__(self):
        self.user_list = {}
        self.schedule = list()

    def save_to_file(self):
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data.json')
            data_file = Path(file)
            with open(data_file, 'w') as f:
                f.write(json.dumps(self.user_list, indent=4))
                f.close()
                return True
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            return False

    async def load_from_file(self):
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data.json')
            session_data_file = Path(file)
            with open(session_data_file, 'r') as f:
                data = json.load(f)
                f.close()
                self.user_list = data
                return True
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            return False

    def user_exists(self, user):
        id_str = str(user.id)
        if id_str in self.user_list:
            return True
        else:
            return False

    async def add_user(self, user):
        if not self.user_exists(user):
            self.user_list[str(user.id)] = {'muted': False}
            self.save_to_file()
            print(f'{user} as been added to the GDQ ping list')
            return True

    async def remove_user(self, user):
        if self.user_exists(user):
            self.user_list.pop(str(user.id))
            print(f'{user} has been removed the GDQ ping list')
            return True

    async def mute(self, user):
        if self.user_exists(user):
            if self.user_list[str(user.id)]['muted'] is False:
                self.user_list[str(user.id)]['muted'] = True
                self.save_to_file()
                print(f'{user} has MUTED the GDQ ping')
                return True

    async def unmute(self, user):
        if self.user_exists(user):
            if self.user_list[str(user.id)]['muted'] is True:
                self.user_list[str(user.id)]['muted'] = False
                self.save_to_file()
                print(f'{user} has UNMUTED the GDQ ping')
                return True

    async def get_schedule(self, ctx):
        limit = 4

        # Prevent out of bounds error
        if len(self.schedule) < 4:
            limit = len(self.schedule)

        schedule_embed = discord.Embed(title="GAMES DONE QUICK 2020", url="https://gamesdonequick.com/schedule",
                                       description=" Please click title for full schedule", color=0x466e9c)
        schedule_embed.set_thumbnail(url="https://gamesdonequick.com/static/res/img/gdqlogo.png")
        now = datetime.now()

        run_datetime = self.strtodatetime(self.schedule[0]["time"])
        if now > run_datetime:
            schedule_embed.add_field(name=f'Playing now: {self.schedule[0]["game"]} ({self.schedule[0]["run"]})',
                                     value=f'By: {self.schedule[0]["runners"]} | '
                                           f'Estimated length: {self.explodeminutes(self.schedule[0]["length"])}',
                                     inline=False)
        else:
            time_remaining = self.diffdates(now, run_datetime)
            schedule_embed.add_field(
                name=f'{time_remaining} until {self.schedule[0]["game"]} ({self.schedule[0]["run"]})',
                value=f'By: {self.schedule[0]["runners"]} | '
                      f'Estimated length: {self.explodeminutes(self.schedule[0]["length"])}',
                inline=False)

        run_pointer = 1
        while run_pointer <= (limit - 1):
            run_datetime = self.strtodatetime(self.schedule[run_pointer]["time"])
            time_remaining = self.diffdates(now, run_datetime)
            schedule_embed.add_field(
                name=f'{time_remaining} until {self.schedule[run_pointer]["game"]} ({self.schedule[run_pointer]["run"]})',
                value=f'By: {self.schedule[run_pointer]["runners"]} | '
                      f'Estimated length: {self.explodeminutes(self.schedule[run_pointer]["length"])}',
                inline=False)

            run_pointer = run_pointer + 1

        await ctx.send(embed=schedule_embed)

    @staticmethod
    def strtodatetime(datetime_str):
        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

    @staticmethod
    def diffdates(now, later):
        diff = later - now
        print(f'{later + diff}')
        hours = divmod(diff.total_seconds(), 3600)[0]
        minutes = divmod(diff.total_seconds(), 60)[0] - (hours * 60)
        return f'{hours:.0f} hrs {minutes:.0f} minutes'

    @staticmethod
    def explodeminutes(minutes):
        hours = int(minutes / 60)
        minutes = minutes - (hours * minutes)

        return f'{hours}:{minutes}'

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
