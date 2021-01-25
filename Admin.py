import asyncio
import os
import json
import discord
from datetime import datetime
from pathlib import Path
from json import JSONDecodeError


class Admin:

    def __init__(self):
        # self.auth_guild_ids = list()
        self.guild_directory = {}
        self.files_loaded = False

    # Get list of initiated guilds
    async def load(self):
        await self.__load_from_file()

    async def mute(self, ctx):
        self.guild_directory[str(ctx.guild.id)]["muted"] = True
        return await self.__save_to_file()

    async def unmute(self, ctx):
        self.guild_directory[str(ctx.guild.id)]["muted"] = False
        return await self.__save_to_file()

    async def give_admin(self, ctx):
        if len(ctx.message.mentions) != 1:
            return False
        else:
            assign_admin_to = ctx.message.mentions[0]
            if assign_admin_to.id not in self.guild_directory[str(ctx.guild.id)]['approved_admins']:
                self.guild_directory[str(ctx.guild.id)]['approved_admins'].append(assign_admin_to.id)
                if assign_admin_to.id not in self.guild_directory[str(ctx.guild.id)]['approved_admins']:
                    return False
                else:
                    await self.__save_to_file()
                    return True

    async def take_admin(self, ctx):
        if len(ctx.message.mentions) != 1:
            return False
        else:
            assign_admin_to = ctx.message.mentions[0]
            if assign_admin_to.id in self.guild_directory[str(ctx.guild.id)]['approved_admins']:
                self.guild_directory[str(ctx.guild.id)]['approved_admins'].remove(assign_admin_to.id)
                if assign_admin_to.id not in self.guild_directory[str(ctx.guild.id)]['approved_admins']:
                    await self.__save_to_file()
                    return True
                else:
                    return False

    async def stop_reminders(self, ctx):
        self.guild_directory[str(ctx.guild.id)]["reminders"] = False
        return await self.__save_to_file()

    async def start_reminders(self, ctx):
        self.guild_directory[str(ctx.guild.id)]["reminders"] = True
        return await self.__save_to_file()

    async def is_guild_admin(self, ctx):
        if str(ctx.guild.id) in self.guild_directory:
            if ctx.author.id in self.guild_directory[str(ctx.guild.id)]['approved_admins']:
                return True
            else:
                return False
        else:
            return False

    async def blacklist(self, bot_owner, guild_owner, ctx, args):
        if len(ctx.message.mentions) > 0:
            member = ctx.message.mentions[0]
            if member.id not in [bot_owner, guild_owner] and not self.is_guild_admin(ctx) and len(args) == 2:

                result = await self.__blacklist_user(ctx.guild.id, member.id)
                if result is True:
                    await ctx.message.add_reaction('✅')
                else:
                    await ctx.message.add_reaction('❌')

    async def permit(self, bot_owner, guild_owner, ctx, args):
        if len(ctx.message.mentions) > 0:
            member = ctx.message.mentions[0]
            if member.id not in [bot_owner, guild_owner] and len(args) == 2:
                result = await self.__permit_user(ctx.guild.id, member.id)
                if result is True:
                    await ctx.message.add_reaction('✅')
                else:
                    await ctx.message.add_reaction('❌')

    def is_user_blacklisted(self, ctx):
        u_id = ctx.author.id
        g_id = str(ctx.guild.id)

        if u_id in self.guild_directory[g_id]['blacklisted']:
            return True
        else:
            return False

    def check_permissions(self, ctx, bot):
        bot_member = ctx.guild.get_member(bot.user.id)
        permissions = ctx.channel.permissions_for(bot_member)
        perm_list = list()
        for perm, value in iter(permissions):
            if value:
                perm_list.append(perm)
        print(perm_list)

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

    async def start(self, ctx, bot):
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
        member = ctx.guild.get_member(member.id)
        try:
            await member.add_roles(role)
            member = ctx.guild.get_member(member.id)
            if any(r.name == role.name for r in member.roles):
                final_report = final_report + f'✅ - \"GDQping\" role can be assigned to members.\n'
            else:
                final_report = final_report + f'❌ - \"GDQping\" role cannot be given to members.\n'
                await ctx.send(final_report + '```')
        except Exception:
            final_report = final_report + f'❌ - \"GDQping\" role cannot be given to members.\n'
            await ctx.send(final_report + '```')
            return

        print(f'{len(role.members)} member(s) from {ctx.guild.name} has the GDQping role')
        print(f'Attempting to remove role from {member.name}')

        # Check if role can be removed
        member = ctx.guild.get_member(member.id)
        await asyncio.sleep(1)
        await member.remove_roles(role)
        if not any(r.name == role.name for r in member.roles):
            final_report = final_report + f'✅ - \"GDQping\" role can be removed from members.\n'
        else:
            final_report = final_report + f'❌ - \"GDQping\" role cannot be removed from members.\n'
            await ctx.send(final_report + '```')
            return

        # Clean slate so no one has role
        print(f'Clearing roles from any other member(s) who has it')
        for member in role.members:
            await member.remove_roles(role)

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

        bot_member = ctx.guild.get_member(bot.user.id)
        permissions = ctx.channel.permissions_for(bot_member)
        perm_list = list()
        for perm, value in iter(permissions):
            if value:
                perm_list.append(perm)

        print(f'Permissions ({ctx.guild.name}): {", ".join(perm_list)}')

        # Add final passage to report
        final_report = final_report + f'\n🎉 - Everything looks good! The bot has been initialized for this guild, ' \
                                      f'please type \"+help\" for instructions ( I recommended pinning this ' \
                                      f'help command, or posting it in the top bar).'
        result, data = await self.__save_new_guild(ctx.guild.id, ctx.channel.id)
        if result is True and data is not None:
            report_ctx = await ctx.send(final_report + '```')
            await check_ctx.delete(delay=15.0)
            await report_ctx.delete(delay=15.0)
        elif result is True and data is None:
            print(f'Data for {ctx.guild.name} already existed.')
        else:
            await ctx.send('```Error saving guild initialization, please contact the developer```')

    async def move(self, ctx, bot):
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
        member = ctx.guild.get_member(member.id)
        try:
            await member.add_roles(role)
            member = ctx.guild.get_member(member.id)
            if any(r.name == role.name for r in member.roles):
                final_report = final_report + f'✅ - \"GDQping\" role can be assigned to members.\n'
            else:
                final_report = final_report + f'❌ - \"GDQping\" role cannot be given to members.\n'
                await ctx.send(final_report + '```')
                return
        except Exception:
            final_report = final_report + f'❌ - \"GDQping\" role cannot be given to members.\n'
            await ctx.send(final_report + '```')
            return

        print(f'{len(role.members)} member(s) from {ctx.guild.name} has the GDQping role')
        print(f'Attempting to remove role from {member.name}')

        # Check if role can be removed
        await member.remove_roles(role)
        member = ctx.guild.get_member(member.id)
        if not any(r.name == role.name for r in member.roles):
            final_report = final_report + f'✅ - \"GDQping\" role can be removed from members.\n'
        else:
            final_report = final_report + f'❌ - \"GDQping\" role cannot be removed from members.\n'
            await ctx.send(final_report + '```')
            return

        # Clean slate so no one has role
        print(f'Clearing roles from any other member(s) who has it')
        for member in role.members:
            await member.remove_roles(role)

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

        bot_member = ctx.guild.get_member(bot.user.id)
        permissions = ctx.channel.permissions_for(bot_member)
        perm_list = list()
        for perm, value in iter(permissions):
            if value:
                perm_list.append(perm)

        print(f'Permissions ({ctx.guild.name}): {", ".join(perm_list)}')

        # Add final passage to report
        final_report = final_report + f'\n🎉 - Everything looks good! The bot has been initialized for this guild, ' \
                                      f'please type \"+help\" for instructions ( I recommended pinning this ' \
                                      f'help command, or posting it in the top bar).'
        result, data = await self.__move_channel(ctx.guild.id, ctx.channel.id)
        # result, data = await self.__save_new_guild(ctx.guild.id, ctx.channel.id)
        if result is True and data is None:
            report_ctx = await ctx.send(final_report + '```')
            if result is True:
                print(f'New data for {ctx.guild.name} saved')
                await check_ctx.delete(delay=15.0)
                await report_ctx.delete(delay=15.0)
        elif result is False:
            await ctx.send(data)

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

    async def __move_channel(self, guild_id, channel_id):
        if str(guild_id) in self.guild_directory:
            self.guild_directory[str(guild_id)]['channels'] = [channel_id]
            result = await self.__save_to_file()
            if result is True:
                return True, None
            else:
                return False, "File error"
        else:
            return False, "Guild doesn't exist."

    @staticmethod
    def __new_guild_model(g_id, c_id):
        return {"guild_id": g_id, "channels": [c_id], "muted": False, "reminders": True, "approved_admins": [],
                "blacklisted": []}

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
        if u_id not in self.guild_directory[str(g_id)]['blacklisted']:
            self.guild_directory[str(g_id)]['blacklisted'].append(u_id)
            if u_id in self.guild_directory[str(g_id)]['blacklisted']:
                return await self.__save_to_file()
            else:
                return False
        else:
            return True

    async def __permit_user(self, g_id, u_id):
        if u_id in self.guild_directory[str(g_id)]['blacklisted']:
            self.guild_directory[str(g_id)]['blacklisted'].remove(u_id)
            if u_id not in self.guild_directory[g_id]['blacklisted']:
                return await self.__save_to_file()
            else:
                return False
        else:
            return True

    async def delete_bot_msg(self, ctx, args):
        if len(args) > 1:
            for arg in args[1:]:
                try:
                    m_id = int(arg)
                    message = await ctx.channel.fetch_message(m_id)
                    await message.delete()
                    print(f'Bot msg: {m_id} deleted by {ctx.author.name}')
                except ValueError:
                    print(f'\'{arg}\' arg is not a valid int')

    async def test_members(self, ctx, bot):
        guild = bot.get_guild(ctx.guild.id)
        print(type(ctx.guild.id))
        role = discord.utils.get(guild.roles, name="GDQping")
        print(f'r_m: {role.members}')

        m1 = list()
        id1 = list()
        for member in role.members:
            print(member)
            m1.append(member.name)
            id1.append(member.id)
            await member.remove_roles(role)
        await ctx.send(f'```{len(id1)} Members will have GDQping role removed: {", ".join(m1)}```')

        await ctx.send(f'{len(role.members)} now have GDQping role \nNow giving them back...')

        for i in id1:
            member = guild.get_member(i)
            await member.add_roles(role)

        await ctx.send(f'{len(role.members)} now have GDQping role: {role.members}')

    async def add_praise(self, message):
        g_id = str(message.guild.id)
        if g_id in self.guild_directory:
            if 'praise' not in self.guild_directory[g_id]:
                self.guild_directory[g_id]['praise'] = 0

            p = self.guild_directory[g_id]['praise']
            self.guild_directory[g_id]['praise'] = p + 1
            await self.__save_to_file()
