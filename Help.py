class Help:

    async def send(self, ctx, args, is_admin):
        if len(args) == 0:
            await ctx.send(self.default())
        elif args[0].lower() == 'sub':
            await ctx.send(self.sub())
        elif args[0].lower() == 'unsub':
            await ctx.send(self.unsub())
        elif args[0].lower() == 'schedule':
            await ctx.send(self.schedule())
        elif args[0].lower() == 'admin' and is_admin:
            await ctx.send(self.admin())
        else:
            await ctx.send(self.default())

    @staticmethod
    def default():
        return '```\n' \
               'GDQping bot - receive notifications when a GDQ run is about to start.\n\n' \
               'Commands:\n' \
               '    +sub - Subcribe to a GDQ run\n' \
               '    +unsub - Unsubscribe to a GDQ run\n' \
               '    +schedule - Get the AGDQ 2021 schedule\n' \
               '    +admin - Only admins (obv) can use these\n\n' \
               'Type +help [category] for more info on that category\n' \
               '\n```'

    @staticmethod
    def sub():
        return '```\n' \
               'Usage:\n' \
               '    +sub 1 (Subscribe to single run)\n' \
               '\n' \
               '    +sub \"1,2,3,4,5\" (Subscribe to multiple runs, quotations recommended)\n' \
               '\n' \
               '    +sub all (Every run will notify you)\n' \
               '\n' \
               '    +sub list (Get a list of your subscriptions sent DM to you)\n\n' \
               'Subscribe to runs by using it\'s ID. The ID can be found on the schedule next to the game name. ' \
               'The \'all\' command does not overwrite your single subscriptions, however it takes priority over ' \
               'your single subscriptions.' \
               '\n```'

    @staticmethod
    def unsub():
        return '```\n' \
               'Usage:\n' \
               '    +unsub 1 (Unsubscribe to single run)\n\n' \
               '    +unsub \"1,2,3,4,5\" (Unsubscribe to multiple runs, quotations recommended)\n\n' \
               '    +unsub all (Every run won\'t notify you)\n\n' \
               '    +unsub purge (Purge all subscriptions, including \'all\' subscription)\n\n' \
               'Unsubscribe to runs by using it\'s ID. The ID can be found on the schedule next to the game name. ' \
               'The \'all\' subscription is a seperate preference from your single subcriptions, you will keep your ' \
               'single subscriptions if you unsub from \'all\'.' \
               '\n```'

    @staticmethod
    def schedule():
        return '```\n' \
               'Usage:\n' \
               '    +schedule (Show 5 next runs on the schedule)\n\n' \
               '    +schedule [\'name\', \'runner\', \'host\'] \"search string\" ' \
                    '(Search for a run using it\'s name, runner, or host)\n\n' \
               'View the latest schedule for AQGDQ 2021. The schedule is sync\'d to the AGDQ schedule every ' \
               'five minutes to reduce inconsistencies.' \
               '\n```'

    # blacklist/permit, resync, mute/unmute, stop/start
    @staticmethod
    def admin():
        return '```\n' \
               'Usage:\n' \
               '    +admin init (*Used once* Initiate a guild into bot\'s guild directory.)\n\n' \
               '    +admin give_admin @user(*GUILD OWNER AND BOT OWNER ONLY* Allow a guild member to use admin)\n\n' \
               '    +admin take_admin @user (*GUILD OWNER AND BOT OWNER ONLY* Remove admin privileges from member)\n\n'\
               '    +admin blacklist @user (The bot will ignore commands issued by this user)\n\n' \
               '    +admin permit @user (Allow the bot to see commands by this user again)\n\n' \
               '    +admin mute (Turn off @role in the reminder message)\n\n' \
               '    +admin unmute (Turn on @role in the reminder messgae)\n\n' \
               '    +admin stop (*NOT WORKING YET* Turn off reminder message)\n\n' \
               '    +admin start (*NOT WORKING YET* Turn on reminder message)\n\n' \
               '    +admin resync (Force a resync to GDQ schedule)\n\n' \
               'Admin commands to control certain aspects of the GDQ ping bot. Please let the developer know if you' \
               ' have any good ideas.' \
               '\n```'

    @staticmethod
    def __template():
        return '```\n' \
               'Usage:\n' \
               '    +unsub 1 (Unsubscribe to single run)\n\n' \
               '    +unsub \"1,2,3,4,5\" (Unsubscribe to multiple runs, quotations recommended)\n\n' \
               '    +unsub all (Every run won\'t notify you)\n\n' \
               '    +unsub purge (Purge all subscriptions, including \'all\' subscription)\n\n' \
               'Unsubscribe to runs by using it\'s ID. The ID can be found on the schedule next to the game name. ' \
               'The \'all\' subscription is a seperate preference from your single subcriptions, you will keep your ' \
               'single subscriptions if you unsub from \'all\'.' \
               '\n```'
