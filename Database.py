import motor.motor_asyncio
from datetime import datetime


class Database:
    def __init__(self):
        # mongodb://localhost:27017
        self.__client = motor.motor_asyncio.AsyncIOMotorClient(
            "mongodb+srv://dbAdmin:pX0rRG4EVDldHYZ4@cluster0.tynhs.mongodb.net/gdqping?retryWrites=true&w=majority")

        __db = self.__client['gdqping']
        self.__guild_info_collection = __db['guild_info']
        self.__schedule_collection = __db['schedule']
        self.__sub_collection = __db['subs']

    async def check_connection(self):
        if "gdqping" in await self.__client.list_database_names():
            return True
        else:
            return False

    async def update_schedule_time_length(self, items_to_update):
        for item in items_to_update:
            query = {"run_id": item["run_id"]}
            values = {"$set": {"time": item['time'], "length": item['length']}}
            await self.__schedule_collection.update_one(query, values)

        if len(items_to_update) > 0:
            print(f'{len(items_to_update)} document(s) have been updated: {datetime.utcnow()}\'')

    async def update_schedule_remind(self, item):
        query = {"run_id": item["run_id"]}
        values = {"$set": {"time": item['reminded']}}
        await self.__schedule_collection.update_one(query, values)

    async def insert_whole_schedule(self, schedule):
        result = await self.__schedule_collection.insert_many(schedule)
        print(f'Inserted {len(result.inserted_ids)} documents')

    async def load_schedule(self):
        full_schedule_list = list()

        async for item in self.__schedule_collection.find({}):
            full_schedule_list.append(item)

        return full_schedule_list

    async def purge_schedule(self):
        await self.__schedule_collection.delete_many({})
        print('%s documents remain' % (await self.__schedule_collection.count_documents({})))

    async def purge_subs(self):
        await self.__sub_collection.delete_many({})
        print('%s documents remain in single sub collection' % (await self.__sub_collection.count_documents({})))

    async def sub_to_all(self, ctx):
        g_id = ctx.message.guild.id
        d_id = ctx.message.author.id

        # Check if item exists already
        q = await self.__sub_collection.find_one({"guild_id": g_id, "discord_id": d_id, "run_id": 0})
        if q is None:
            # if not, insert new item
            result = await self.__sub_collection.insert_one({"guild_id": g_id, "discord_id": d_id, "run_id": 0})
            if result is not None:
                return True
            else:
                return False
        return True

    async def sub_to_game(self, ctx, run_id):
        g_id = ctx.message.guild.id
        r_id = run_id
        d_id = ctx.message.author.id
        k = {"guild_id": g_id, "run_id": r_id, "discord_id": d_id}
        result = await self.__sub_collection.update(k, k, upsert=True)
        print(result)

    async def sub_to_many_games(self, runs_to_insert):
        num_of_inserts = len(runs_to_insert)
        inserted_items = 0
        for run in runs_to_insert:
            result = await self.__sub_collection.update_one({"index": run}, {"$setOnInsert": runs_to_insert[run]},
                                                            upsert=True)
            if result.modified_count == 1:
                inserted_items = inserted_items + 1

        if num_of_inserts == inserted_items:
            return True
        else:
            return False

    async def unsub_to_all(self, ctx):
        g_id = ctx.message.guild.id
        d_id = ctx.message.author.id

        q = await self.__sub_collection.find_one({"guild_id": g_id, "discord_id": d_id, "run_id": 0})

        if q is not None:
            await self.__sub_collection.delete_one({"guild_id": g_id, "discord_id": d_id, "run_id": 0})
            q = await self.__sub_collection.find_one({"guild_id": g_id, "discord_id": d_id, "run_id": 0})
            if q is None:
                return True
            else:
                return False
        else:
            return True

    async def unsub_to_game(self, ctx, run_id):
        g_id = ctx.message.guild.id
        r_id = run_id
        d_id = ctx.message.author.id

        q = await self.__sub_collection.find_one({"guild_id": g_id, "run_id": r_id, "discord_id": d_id})

        if q is not None:
            await self.__sub_collection.delete_one({"guild_id": g_id, "run_id": r_id, "discord_id": d_id})
            q = await self.__sub_collection.find_one({"guild_id": g_id, "run_id": r_id, "discord_id": d_id})
            if q is None:
                return True
            else:
                return False
        else:
            return True

    async def unsub_to_many_games(self, runs_to_remove):
        num_of_removals = len(runs_to_remove)
        removed_items = 0
        for run in runs_to_remove:
            result = await self.__sub_collection.delete_one({"index": run})
            if result.deleted_count == 1:
                removed_items = removed_items + 1

        if num_of_removals == removed_items:
            return True
        else:
            return False

    async def get_subs_by_guild(self, run_id, guild_id):
        sub_list = await self.__sub_collection.find({
            "$and": [
                {"run_id": 0}, {"run_id": run_id}
            ],
            "guild_id": guild_id})

        # Find duplitcate items and remove them, run 0 take priority
        cleaned_list = list()
        for sub in sub_list:
            if sub["run_id"] == 0:
                cleaned_list.append(sub)
            elif sub["run_id"] == run_id:
                if not any(s["discord_id"] == sub["discord_id"] and s["run_id"] == 0 for s in sub_list):
                    cleaned_list.append(sub)

        return cleaned_list

    async def get_subs_by_user(self, discord_id):
        return await self.__sub_collection.find({"discord_id": discord_id}).sort("run_id", 1).to_list(length=151)

    async def purge_subs_by_user(self, discord_id, guild_id):
        await self.__sub_collection.delete_many({"discord_id": str(discord_id), "guild_id": str(guild_id)})

        result = await self.__sub_collection.find({"discord_id": discord_id}).to_list(length=151)
        if len(result) == 0:
            return True
        else:
            print(result)
            return False

    async def save_new_guild(self, data_to_save):
        guild = await self.__guild_info_collection.find_one({"guild_id": data_to_save["guild_id"]})

        if guild is None:
            await self.__guild_info_collection.insert_one(data_to_save)

            guild = await self.__guild_info_collection.find_one({"guild_id": data_to_save["guild_id"]})
            if guild is not None:
                return True
            else:
                return False
        else:
            return True

    async def delete_subs_by_run_id(self, run_id):
        # Get previous run id
        prev_run_id = run_id - 1

        if run_id > 0:
            pass
        else:
            return False

    async def get_guild_info(self):
        db_info_list = list()
        async for doc in self.__guild_info_collection.find({}):
            db_info_list.append(doc)
        return db_info_list

    async def give_admin_to_user(self, user_id, guild_id):
        # Pull old doc
        guild_info = await self.__guild_info_collection.find_one({"guild_id": guild_id})

        # Check if user_id is in old doc
        if user_id not in guild_info['approved_admins']:
            guild_info['approved_admins'].append(user_id)
        else:
            return True

        # If it wasn't, send update
        self.__guild_info_collection.replace_one({"guild_id": guild_id}, guild_info)

        # Validate doc
        guild_info = await self.__guild_info_collection.find_one({"guild_id": guild_id})
        if user_id in guild_info['approved_admins']:
            return True
        else:
            return False

    async def blacklist_user(self, guild_id, user_id):
        guild_blacklist = await self.__guild_info_collection.find_one({"guild_id": guild_id},
                                                                      {"blacklisted": 1})

        if user_id not in guild_blacklist['blacklisted']:
            guild_blacklist['blacklisted'].append(user_id)
            query = {"guild_id": guild_id}
            values = {"$set": {"blacklisted": guild_blacklist['blacklisted']}}
            await self.__guild_info_collection.update_one(query, values)

            guild_blacklist = await self.__guild_info_collection.find_one({"guild_id": guild_id},
                                                                          {"blacklisted": 1})
            if user_id in guild_blacklist['blacklisted']:
                return True
            else:
                return False
        else:
            return True

    async def permit_user(self, guild_id, user_id):
        guild_blacklist = await self.__guild_info_collection.find_one({"guild_id": guild_id},
                                                                      {"blacklisted": 1})

        if user_id in guild_blacklist['blacklisted']:
            guild_blacklist['blacklisted'].remove(user_id)
            query = {"guild_id": guild_id}
            values = {"$set": {"blacklisted": guild_blacklist['blacklisted']}}
            await self.__guild_info_collection.update_one(query, values)

            guild_blacklist = await self.__guild_info_collection.find_one({"guild_id": guild_id},
                                                                          {"blacklisted": 1})
            if user_id not in guild_blacklist['blacklisted']:
                return True
            else:
                return False
        else:
            return True
