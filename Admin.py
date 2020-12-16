import os
import json
import discord
from datetime import datetime
from pathlib import Path
from json import JSONDecodeError


class Admin:

    def __init__(self, database):
        # self.auth_guild_ids = list()
        self.guild_directory = {}
        self.database = database

    # Get list of initiated guilds
    async def load(self):
        # db_guild_list = await self.database.get_guild_info()
        # for guild in db_guild_list:
        #     self.guild_directory[str(guild['guild_id'])] = guild
        await self.__load_from_file()

    async def give_admin(self, ctx):
        if len(ctx.message.mentions) != 1:
            return False
        else:
            assign_admin_to = ctx.message.mentions[0]
            result = await self.database.give_admin_to_user(assign_admin_to.id, ctx.guild.id)
            if result is True:
                self.guild_directory[str(ctx.guild.id)]['approved_admins'].append(assign_admin_to.id)
                return True
            else:
                return False

    async def is_guild_admin(self, ctx):
        if ctx.author.id in self.guild_directory[str(ctx.guild.id)]['approved_admins']:
            return True
        else:
            return False

    async def blacklist(self, bot_owner, guild_owner, ctx, args):
        if len(ctx.message.mentions) > 0:
            member = ctx.message.mentions[0]
            if member.id not in [bot_owner, guild_owner] and len(args) == 2:

                result = await self.__blacklist_user(ctx.guild.id, member.id)
                if result is True:
                    await ctx.message.add_reaction('✅')
                    await self.database.blacklist_user(ctx.guild.id, member.id)
                else:
                    await ctx.message.add_reaction('❌')

    async def permit(self, bot_owner, guild_owner, ctx, args):
        if len(ctx.message.mentions) > 0:
            member = ctx.message.mentions[0]
            if member.id not in [bot_owner, guild_owner] and len(args) == 2:
                result = await self.__permit_user(ctx.guild.id, member.id)
                if result is True:
                    await ctx.message.add_reaction('✅')
                    await self.database.permit_user(ctx.guild.id, member.id)
                else:
                    await ctx.message.add_reaction('❌')

    def is_user_blacklisted(self,ctx):
        u_id = str(ctx.author.id)
        g_id = str(ctx.guild.id)

        if u_id in self.guild_directory[g_id]['blacklisted']:
            return True
        else:
            return False

    def if_guild_init(self, g_id):
        if str(g_id) in self.guild_directory:
            return True
        else:
            return False

    def if_registered_channel(self, ctx):
        g_key = str(ctx.guild.id)
        if ctx.channel.id in self.guild_directory[g_key]['channels']:
            return True
        else:
            return False

    async def start(self, ctx):
        check_ctx = await ctx.send('Please wait checking guild permissions and settings...')
        final_report = '```Report:\n'
        member = ctx.author

        # Check if gdqping role exists
        role = discord.utils.get(ctx.guild.roles, name="GDQping")
        if role is None:
            final_report = final_report + f'❌ - \"GDQping\" role is missing, it is critical to the bot. It will be ' \
                                          f'used for notifying users when a run is about to start.\n'
            await ctx.send(final_report + '```')
            return
        else:
            final_report = final_report + f'✅ - \"GDQping\" role is present.\n'

        # Check if role can be assigned
        await member.add_roles(role)
        member = await ctx.guild.fetch_member(member.id)
        if any(r.name == role.name for r in member.roles):
            final_report = final_report + f'✅ - \"GDQping\" role can be assigned to members.\n'
        else:
            final_report = final_report + f'❌ - \"GDQping\" role cannot be given to members.\n'
            await ctx.send(final_report + '```')
            return

        # Check if role can be removed
        await member.remove_roles(role)
        member = await ctx.guild.fetch_member(member.id)
        if not any(r.name == role.name for r in member.roles):
            final_report = final_report + f'✅ - \"GDQping\" role can be removed from members.\n'
        else:
            final_report = final_report + f'❌ - \"GDQping\" role cannot be removed from members.\n'
            await ctx.send(final_report + '```')
            return

        # Check add reactions
        await check_ctx.add_reaction('❌')
        await check_ctx.add_reaction('✅')
        check1 = False
        check2 = False
        check_ctx = await check_ctx.channel.fetch_message(check_ctx.id)
        for reaction in check_ctx.reactions:
            if reaction.emoji == '❌':
                check1 = True
            elif reaction.emoji == '✅':
                check2 = True

        if check1 is True and check2 is True:
            final_report = final_report + f'✅ - Reactions can be added to messages.\n'
        else:
            final_report = final_report + f'❌ - Reactions cannot be added to messages.\n'
            await ctx.send(final_report + '```')
            return

        # Check remove reactions
        await check_ctx.remove_reaction('❌', check_ctx.author)
        await check_ctx.remove_reaction('✅', check_ctx.author)
        check_ctx = await check_ctx.channel.fetch_message(check_ctx.id)
        if len(check_ctx.reactions) == 0:
            final_report = final_report + f'✅ - Reactions can be removed from messages.\n'
        else:
            final_report = final_report + f'❌ - Reactions cannot be removed from messages.\n'
            await ctx.send(final_report + '```')
            return

        # Check if it can only see this channel
        channels = ctx.guild.channels
        if len(channels) > 1:
            final_report = final_report + f'💬 - Although the bot can see many channels, it will be ' \
                                          f'restricted to this channel. So, its commands will only work here.'
        elif len(channels) == 1:
            final_report = final_report + f'✅ - The bot is restricted only to this channel.\n'

        # Add final passage to report
        final_report = final_report + f'\n🎉 - Everything looks good! The bot has been initialized for this guild, ' \
                                      f'please type \"+help\" for instructions ( I recommended pinning this ' \
                                      f'help command, or posting it in the top bar).'
        result, data = await self.__save_new_guild(ctx.guild.id, ctx.channel.id)
        if result is True and data is not None:
            await ctx.send(final_report + '```')
            result = await self.database.save_new_guild(data)
            if result is True:
                print(f'New data for {ctx.guild.name} saved to database')
            else:
                print(f'Could not save data for {ctx.guild.name}')
        elif result is True and data is None:
            print(f'Data for {ctx.guild.name} already existed.')
        else:
            await ctx.send('```Error saving guild initialization, please contact the developer```')

    async def __save_new_guild(self, guild_id, channel_id):

        if str(guild_id) in self.guild_directory:
            return True, None
        else:
            new_guild = self.__new_guild_model(guild_id, channel_id)
            self.guild_directory[str(guild_id)] = new_guild
            result = await self.__save_to_file()
            if result is True:
                return True, new_guild
            else:
                return False, None

    @staticmethod
    def __new_guild_model(g_id, c_id):
        return {"guild_id": str(g_id), "channels": [str(c_id)], "approved_admins": [], "blacklisted": []}

    async def __load_from_file(self):
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data/guild_directory.json')
            session_data_file = Path(file)
            with open(session_data_file, 'r') as f:
                data = json.load(f)
                f.close()
                self.guild_directory = data
                return True
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            return False

    async def __save_to_file(self):
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data/guild_directory.json')
            data_file = Path(file)
            with open(data_file, 'w') as f:
                f.write(json.dumps(self.guild_directory, indent=4))
                f.close()
                return True
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            now = datetime.utcnow()
            date_string = now.strftime("%m_%d_%Y_%H_%M_%S")
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, f'data/guild_directory_dump_{date_string}.txt')
            data_file = Path(file)
            with open(data_file, 'w') as f:
                print(self.guild_directory, file=f)
                print(f'Error dumped to /guild_directory_dump_{date_string}.txt')
                f.close()
            return False

    async def __blacklist_user(self, g_id, u_id):
        if str(u_id) not in self.guild_directory[str(g_id)]['blacklisted']:
            self.guild_directory[str(g_id)]['blacklisted'].append(str(u_id))
            if str(u_id) in self.guild_directory[str(g_id)]['blacklisted']:
                return await self.__save_to_file()
            else:
                return False
        else:
            return True

    async def __permit_user(self, g_id, u_id):
        if str(u_id) in self.guild_directory[str(g_id)]['blacklisted']:
            self.guild_directory[str(g_id)]['blacklisted'].remove(str(u_id))
            if str(u_id) not in self.guild_directory[str(g_id)]['blacklisted']:
                return await self.__save_to_file()
            else:
                return False
        else:
            return True
