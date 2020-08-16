import os
import json
import discord
from pathlib import Path
from json import JSONDecodeError
from datetime import datetime,timedelta
import csv

class DataHandler:
    def __init__(self):
        self.user_list = {}
        self.schedule = list()
        self.ping_role_name = "GDQping"
        self.delay = 0

    def user_exists(self, user):
        id_str = str(user.id)
        if id_str in self.user_list:
            return True
        else:
            return False

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

        # Prevent out of bounds error
        if len(self.schedule) < 4:
            limit = len(self.schedule)

        schedule_embed = discord.Embed(title="GAMES DONE QUICK 2020 - Coming up",
                                       url="https://gamesdonequick.com/schedule",
                                       description=" Please click title for full schedule", color=0x466e9c)
        schedule_embed.set_thumbnail(url="https://gamesdonequick.com/static/res/img/gdqlogo.png")
        now = datetime.now()
        delay_delta = await self.get_delay_delta()
        run_datetime = self.strtodatetime(self.schedule[0]["time"]) + delay_delta
        if now > run_datetime:
            schedule_embed.add_field(name=f'Playing now: {self.schedule[0]["game"]} ({self.schedule[0]["run"]})',
                                     value=f'By: {self.schedule[0]["runners"]} | '
                                           f'Estimated length: {self.explodeminutes(self.schedule[0]["length"])}',
                                     inline=False)
        else:
            time_remaining = self.diffdates(now, run_datetime)
            schedule_embed.add_field(
                name=f'{self.schedule[0]["game"]} ({self.schedule[0]["run"]}) in {time_remaining}',
                value=f'By: {self.schedule[0]["runners"]} | '
                      f'Estimated length: {self.explodeminutes(self.schedule[0]["length"])}',
                inline=False)

        run_pointer = 1
        while run_pointer <= (limit - 1):
            run_datetime = self.strtodatetime(self.schedule[run_pointer]["time"]) + delay_delta
            time_remaining = self.diffdates(now, run_datetime)
            schedule_embed.add_field(
                name=f'{self.schedule[run_pointer]["game"]} ({self.schedule[run_pointer]["run"]}) in {time_remaining}',
                value=f'By: {self.schedule[run_pointer]["runners"]} | '
                      f'Estimated length: {self.explodeminutes(self.schedule[run_pointer]["length"])}',
                inline=False)

            run_pointer = run_pointer + 1
        await ctx.send(content="https://www.twitch.tv/gamesdonequick", embed=schedule_embed)

    @staticmethod
    def strtodatetime(datetime_str):
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
        minutes = minutes - (hours * minutes)

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
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'gdq2020schedule.json')
            data_file = Path(file)
            with open(data_file, 'w') as f:
                f.write(json.dumps(self.schedule, indent=4))
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

    '''

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

            async def save_to_file(self):
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
       '''
