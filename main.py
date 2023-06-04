import threading
import traceback
import os
import json
import httpx
import datetime
import asyncio
from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# DISCORD LIBS
import discord
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions
from discord import Embed, Permissions

# FLASK
from flask import Flask, request, jsonify
import waitress

Base = declarative_base()

ListToSend = []

def anti_sql(string):
    sqlblacklist = list("'[]{},./?=-|)(*^")
    if any(ext in string for ext in sqlblacklist):
        return True


class Member(Base):
    __tablename__ = 'members'
    id = Column(Integer, primary_key=True)
    json = Column(String, nullable=False)


class Db:
    def __init__(self) -> None:
        self.engine = create_engine("sqlite:///Members.db")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def get_members(self):
        return self.session.query(Member).all()

    def add_new_member(self, json_data):
        member = Member(json=json_data)
        self.session.add(member)
        self.session.commit()

    def update_member(self, old_json, new_json):
        member = self.session.query(Member).filter_by(json=old_json).first()
        member.json = new_json
        self.session.commit()

    def check_if_user_in_db(self, json_data):
        return self.session.query(Member).filter_by(json=json_data).first()


member_db = Db()


class Discordx:
    def __init__(self):
        config = json.loads(open("config.json", "r").read())
        self.bot_token = config['BOT_TOKEN']
        self.server_id = config['SERVER_ID']
        self.client_id = config['CLIENT_ID']
        self.client_sec = config['CLIENT_SEC']
        self.redirect_url = config['REDIRECT_URL']

    def exchange_code(self, code):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_sec,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_url,
        }
        r = httpx.post(f"https://discord.com/api/v9/oauth2/token", data=data, headers=headers)
        return r.json()

    def get_info(self, access_token):
        headers = {'Authorization': 'Bearer ' + access_token}
        response = httpx.get("https://discord.com/api/v9/users/@me", headers=headers)
        return response.json()

    def get_new_token(self, refresh_token):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_sec,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        r = httpx.post("https://discord.com/api/v9/oauth2/token", data=data, headers=headers)
        return r.json()

    def add_to_guild(self, access_token, user_id, guild_id):
        headers = {
            "Authorization": f"Bot {self.bot_token}",
            'Content-Type': 'application/json'
        }
        data = {"access_token": access_token}
        url = f"https://discordapp.com/api/v9/guilds/{guild_id}/members/{user_id}"
        response = httpx.put(url=url, headers=headers, json=data)
        return response.json()


class Tools:
    def __init__(self) -> None:
        config = json.loads(open("config.json", "r").read())
        self.bot_token = config['BOT_TOKEN']
        self.server_id = config['SERVER_ID']
        self.client_id = config['CLIENT_ID']
        self.client_sec = config['CLIENT_SEC']
        self.log_channel = config['LOG_CHANNEL']
        self.role_name = config['ROLE_NAME']
        self.password = config['PASSWORD']
        self.redirect_url = config['REDIRECT_URL']
        self.backup_every = config['BACKUP_EVERY_SEC']
        self.backup_message_count = config['BACKUP_MESSAGE_COUNT']

    def discord_bot(self):
        bot = commands.Bot(command_prefix=".", help_command=None, intents=discord.Intents.all(), activity=discord.Game(name="BackupCord"))

        @bot.command()
        async def message(ctx):

            client_id = self.client_id
            redirect_url = self.redirect_url

            class View(discord.ui.View):
                def __init__(self):
                    super().__init__()
                    button = discord.ui.Button(label='Verification',emoji="✅", style=discord.ButtonStyle.url, url='https://discord.com/oauth2/authorize?response_type=code&client_id='+client_id+'&scope=identify+guilds.join&redirect_uri='+redirect_url)
                    self.add_item(button)

            view = View()

            await ctx.send(view=view)



        @bot.command()
        @has_permissions(administrator=True)
        async def bmembers(ctx, arg):
            if arg == self.password:
                members = member_db.get_members()
                added = 0
                for member in members:
                    try:
                        json_data = json.loads(member.json)
                        refresh_token = json_data['refresh_token']
                        user_id = json_data['userid']
                        res = Discordx().get_new_token(refresh_token)
                        if "access_token" in res:
                            access_token = res['access_token']
                            refresh_token = res['refresh_token']
                            json_data['access_token'] = access_token
                            json_data['refresh_token'] = refresh_token
                            member_db.update_member(json.dumps(json_data), member.json)
                            res = Discordx().add_to_guild(access_token, user_id, ctx.message.guild.id)
                            try:
                                res['joined_at']
                                res['avatar']
                                res['user']
                                added += 1
                            except:
                                pass
                    except:
                        pass

                embed = Embed(title='', description=f"**✅ | Member restored**\n≡ | Members added : {added}", color=discord.Color.from_rgb(87, 147, 255))
                await ctx.channel.send(embed=embed)

        @bot.command()
        @has_permissions(administrator=True)
        async def bserver(ctx, file_name):
            guild = ctx.guild

            with open(file_name, "r") as f:
                server_settings = json.load(f)
                print("Server recovery started...")

                async def remove_category(ctx: commands.Context):
                    for category in ctx.guild.categories:
                        try:
                            await category.delete()
                        except:
                            pass

                async def remove_channels(ctx: commands.Context):
                    for channel in ctx.guild.channels:
                        try:
                            await channel.delete()
                        except:
                            pass

                async def remove_roles(ctx: commands.Context):
                    for role in ctx.guild.roles:
                        if role == ctx.guild.default_role:
                            continue
                        else:
                            try:
                                await role.delete()
                            except:
                                pass

                tasks = [remove_channels(ctx), remove_roles(ctx), remove_category(ctx)]
                await asyncio.gather(*tasks)

                try:
                    await ctx.guild.edit(name=server_settings['name'], icon=httpx.get(server_settings['icon_url']).content)
                except:
                    pass
                
                roles = server_settings['roles']
                categories = server_settings['categories']

                for role in reversed(roles):
                    if role['name'] != '@everyone':
                        new_role = await guild.create_role(name=role['name'], permissions=Permissions(role['permissions']), colour=int(role['colour'][1:], 16))
                        roles[roles.index(role)]['id'] = new_role.id
                    else:
                        await guild.default_role.edit(permissions=Permissions(role['permissions']))
                        roles[roles.index(role)]['id'] = guild.default_role.id

                async def create_channels(category, channel):
                    new_channel = await category.create_text_channel(name=channel['name'])
                    for message in channel['history']:
                        embed = Embed(description=message['content'], timestamp=datetime.datetime.fromisoformat(message['timestamp']))
                        author = discord.utils.get(category.guild.members, id=message['author']['id'])
                        embed.set_author(name=message['author']['name'])
                        embed.set_footer(text=f"User id: {message['author']['id']}")
                        await new_channel.send(embed=embed)

                for category in categories:
                    new_category = await guild.create_category(name=category['name'])
                    for channel in category['channels']:
                        await create_channels(new_category, channel)

                print("Server recovery done")

        class Data():
            time = 0

        @tasks.loop(seconds=3)
        async def member_sec():
            Data.time += 1
            guild = bot.get_guild(int(self.server_id))
            for member in ListToSend:
                member_count = str(len(member_db.get_members()))
                channel = discord.utils.get(guild.channels, id=int(self.log_channel))
                embed = Embed(title='', description=f"**✅ | Member verified**\n≡ | User: <@{member['userid']}>\n≡ | Address: ||{member['ip']}||\n≡ | Members in db: `{member_count}`", color=discord.Color.from_rgb(87, 147, 255))
                await channel.send(embed=embed)
                role = discord.utils.get(guild.roles, name=self.role_name)
                try:
                    member_obj = await guild.fetch_member(int(member['userid']))
                    await member_obj.add_roles(role)
                except:
                    traceback.print_exc()


            ListToSend.clear()


            if (Data.time == 1) or (Data.time >= int(self.Backup_every) / 3):
               
                print("Creating backup...")

                try:
                    server_settings = {}

                    server_settings['name'] = guild.name
                    try:
                        server_settings['icon_url'] = str(guild.icon)
                    except:
                        pass

                    roles = []
                    for role in guild.roles:
                        if role.name != "Server Booster":
                            roles.append({"name": role.name, "permissions": role.permissions.value, "colour": str(role.color)})

                    server_settings['roles'] = roles

                    emojis = []
                    for emoji in guild.emojis:
                        emojis.append({"name": emoji.name, "url": str(emoji.url)})

                    server_settings['emojis'] = emojis

                    categories = []
                    for category in guild.categories:
                        channels = []
                        overwrites = []
                        for channel in category.channels:
                            history = []
                            try:
                                async for message in channel.history(limit=self.Backup_message_count):
                                    history.append({
                                        "content": message.content,
                                        "timestamp": message.created_at.isoformat(),
                                        "author": {
                                            "id": message.author.id,
                                            "name": message.author.name,
                                        }
                                    })
                            except:
                                pass
                            overwrites = []
                            for overwrite in channel.overwrites:
                                if isinstance(overwrite, discord.Role):
                                    overwrites.append({"id": overwrite.id, "allow": overwrite.permissions})

                            channels.append({
                                "name": channel.name,
                                "overwrites": overwrites,
                                "history": history
                            })

                        overwrites = []
                        for overwrite in category.overwrites:
                            if isinstance(overwrite, discord.Role):
                                overwrites.append({"id": overwrite.id, "allow": overwrite.permissions})

                        categories.append({
                            "name": category.name,
                            "overwrites": overwrites,
                            "channels": channels
                        })

                    server_settings['categories'] = categories


                    with open(f"backup/{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json", "w") as f:
                        json.dump(server_settings, f,  default=lambda obj: obj.value if isinstance(
                            obj, discord.Permissions) else obj.__dict__)

                    channel = discord.utils.get(
                        guild.channels, id=int(self.Log_channel))
                    embed = discord.Embed(title='', description=f"""**⚡️ | Backup created**
                    ≡ | Time: `backup/{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S.json')}`""", color=5763719)
                    await channel.send(embed=embed)

                    print("Backup Done")
                    Data.time = 6
                except:
                    pass


        @bot.event
        async def on_ready():
            os.system("cls")
            print("Bot started")
            member_sec.start()

        bot.run(self.bot_token)

class ApiBot:
    def __init__(self):
        self.run_api()

    def run_api(self):
        app = Flask(__name__)

        @app.route('/auth')
        def auth():
            code = request.args.get("code")

            if code is not None:
                if anti_sql(code):
                    return jsonify({"error": "1004"})

                discord = Discordx()
                res = discord.exchange_code(code)
                try:
                    access_token = res['access_token']
                    refresh_token = res['refresh_token']
                    info = discord.get_info(access_token)
                    username = info['username']
                    avatar = info['avatar']
                    userid = info['id']
                except:
                    return jsonify({"error": "1005"})
                data = {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "username": username,
                    "avatar": avatar,
                    "userid": userid,
                    "ip": request.remote_addr
                }

                if not member_db.check_if_user_in_db(json.dumps(data)):
                    member_db.add_new_member(json.dumps(data))
                ListToSend.append(data)
                return "<script>window.close();</script>"
            else:
                return jsonify({"error": "1002"})

        waitress.serve(app, host="0.0.0.0", port=80)

if __name__ == "__main__":
    threading.Thread(target=ApiBot).start()
    Tools().discord_bot()
