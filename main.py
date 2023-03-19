import threading
import os
import json
import tracemalloc
import httpx
import sqlite3
import datetime
import asyncio
from dotenv import load_dotenv
from requests.api import request

# DISCORD LIBS
import discord
import discord.ext
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions
from discord.utils import get
from discord import Permissions, Embed
from discord_ui import UI, LinkButton, Button

# FLASK
from flask import Flask, redirect, request, jsonify
import waitress


def AntiSql(string):
    sqlblacklist = list("'[]{},./?=-|)(*^")
    if any(ext in string for ext in sqlblacklist):
        return True


load_dotenv()
tracemalloc.start()
event = threading.Event()

config = json.loads(open("config.json", "r").read())


class Db:
    def __init__(self) -> None:
        self.DataBase = sqlite3.connect("Members.db", check_same_thread=False)
        self.Cursor = self.DataBase.cursor()
        self.CreateDb()

    def CreateDb(self):

        sql_table_payload = """ CREATE TABLE IF NOT EXISTS members (
                                id integer PRIMARY KEY,
                                json text NOT NULL
                                ); """

        self.Cursor.execute(sql_table_payload)
        self.DataBase.commit()
        self.DataBase.commit()

    def GetMembers(self):
        self.Cursor.execute('SELECT id, json FROM members')

        records = self.Cursor.fetchall()
        if records == []:
            return 1001
        return list(records)

    def AddNewMember(self, jsonx):
        self.Cursor.execute(
            "insert into members (json) values ('"+json.dumps(jsonx)+"');")
        self.DataBase.commit()

    def UpdateMember(self, json0, json1):
        self.Cursor.execute("UPDATE members SET json = '" +
                            json0+"' WHERE json = '"+json1+"'")
        self.DataBase.commit()

    def CheckIfUserIsInDb(self, jsonx):
        self.Cursor.execute(
            "SELECT json FROM members WHERE json='{0}'".format(json.dumps(jsonx)))
        records = self.Cursor.fetchall()
        if records == []:
            return False
        else:
            return records


Memberdb = Db()


class Discordx:
    def __init__(self) -> None:

        self.BotToken = config['BOT_TOKEN']
        self.ServerId = config['SERVER_ID']
        self.Client_id = config['CLIENT_ID']
        self.Client_sec = config['CLIENT_SEC']
        self.Redirect_url = config['REDIRECT_URL']

    def ExchangeCode(self, code):

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'client_id': self.Client_id, 'client_secret': self.Client_sec, 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': self.Redirect_url,
                # 'scope': "identify guilds guilds.join"
                }
        r = httpx.post(f"https://discord.com/api/v9/oauth2/token",
                       data=data, headers=headers)
        return r.json()

    def GetInfo(self, code):
        headers = {'Authorization': 'Bearer ' + code, }
        response = httpx.get(
            "https://discord.com/api/v9/users/@me", headers=headers)
        return response.json()

    def GetNewToken(self, token):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'client_id': self.Client_id,
            'client_secret': self.Client_sec,
            'grant_type': 'refresh_token',
            'refresh_token': token
        }
        r = httpx.post("https://discord.com/api/v9/oauth2/token",
                       data=data, headers=headers)
        return r.json()

    def AddToGuild(self, access_token, user_id, guild_id):

        headers = {
            "Authorization": f"Bot {self.BotToken}",
            'Content-Type': 'application/json'
        }

        data = {"access_token": access_token}

        url = f"https://discordapp.com/api/v9/guilds/{guild_id}/members/{user_id}"
        response = httpx.put(
            url=url,
            headers=headers,
            json=data
        )
        return response.json()


ListToSend = []


class Tools:
    def __init__(self) -> None:
        self.BotToken = config['BOT_TOKEN']
        self.ServerId = config['SERVER_ID']
        self.Client_id = config['CLIENT_ID']
        self.Client_sec = config['CLIENT_SEC']
        self.Log_channel = config['LOG_CHANNEL']
        self.Role_name = config['ROLE_NAME']
        self.Password = config['PASSWORD']
        self.Redirect_url = config['REDIRECT_URL']
        self.Backup_every = config['BACKUP_EVERY_SEC']
        self.Backup_message_count = config['BACKUP_MESSAGE_COUNT']

    def discordbot(self):

        self.bot = commands.Bot(command_prefix=".", help_command=None, intents=discord.Intents(
        ).all(), activity=discord.Game(name="BackupCord"))
        self.ui = UI(self.bot)

        @self.bot.command()
        async def message(ctx):

            embed = discord.Embed(
                color=5763719, description=f"__**Verification**__")
            
            await ctx.message.channel.send(embed=embed, components=[
             LinkButton('https://discord.com/oauth2/authorize?response_type=code&client_id='+self.Client_id+'&scope=identify+guilds.join&redirect_uri='+self.Redirect_url, emoji="✅")],
            
        )

        @self.bot.command()
        @has_permissions(administrator=True)
        async def bmembers(ctx, arg):
            if arg == self.Password:
                members = Memberdb.GetMembers()
                global added
                added = 0
                for i in members:
                    try:
                        x = json.loads(i[1])
                        refresh_token = x['refresh_token']
                        user_id = x['userid']
                        res = Discordx().GetNewToken(refresh_token)
                        if not "error" in res:
                            access_token = res['access_token']
                            refresh_token = res['refresh_token']
                            x['access_token'] = access_token
                            x['refresh_token'] = refresh_token
                            Memberdb.UpdateMember(json.dumps(x), i[1])
                            res = Discordx().AddToGuild(access_token, user_id, ctx.message.guild.id)
                            try:
                                res['joined_at']
                                res['avatar']
                                res['user']
                                added = added + 1
                            except:
                                pass
                    except:
                        pass

                embed = discord.Embed(title='', description="""
**✅ | Member restored**

≡ | Members added : {0}

""".format(str(added)), color=5763719)
            await ctx.channel.send(embed=embed)


        @self.bot.command()
        @has_permissions(administrator=True)
        async def bserver(ctx, file_name):
            guild = ctx.guild

            with open(file_name, "r") as f:
                server_settings = json.load(f)
                print("Server recovery started...")

                async def remove_category(ctx: commands.Context):
                    for category in ctx.guild.categories:
                        try: await category.delete()
                        except: pass

                async def remove_channels(ctx: commands.Context):
                    for channel in ctx.guild.channels:
                        try: await channel.delete()
                        except: pass

                async def remove_roles(ctx: commands.Context):
                    for role in ctx.guild.roles:
                        if role == ctx.guild.default_role: continue
                        else:
                            try: await role.delete()
                            except: pass

                tasks = [remove_channels(ctx), remove_roles(ctx), remove_category(ctx)]
                await asyncio.gather(*tasks)

                await ctx.guild.edit(name=server_settings['name'], icon=httpx.get(server_settings['icon_url']).content)

                roles = server_settings['roles']
                categories = server_settings['categories']

                for role in reversed(roles):
                    if role['name'] != '@everyone':
                        new_role = await guild.create_role(name=role['name'], permissions=discord.Permissions(role['permissions']),  colour=int(role['colour'][1:], 16))
                        roles[roles.index(role)]['id'] = new_role.id
                    else:
                        await guild.default_role.edit(permissions=discord.Permissions(role['permissions']))
                        roles[roles.index(role)]['id'] = guild.default_role.id


                async def create_channels(category, channel):
                    new_channel = await category.create_text_channel(name=channel['name'])
                    for message in channel['history']:
                        embed = discord.Embed(description=message['content'], timestamp=datetime.datetime.fromisoformat(message['timestamp']))
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
        async def MemberSec():
            Data.time += 1
            guild = self.bot.get_guild(int(self.ServerId))
            for i in ListToSend:
                membercount = str(len(Memberdb.GetMembers()))
                channel = discord.utils.get(
                    guild.channels, id=int(self.Log_channel))
                embed = discord.Embed(title='', description="""**✅ | Member verified**
                ≡ | User: <@{0}>
                ≡ | Address: ||{1}||
                ≡ | Members in db: `{2}`""".format(i['userid'], i['ip'], membercount), color=5763719)
                await channel.send(embed=embed)
                role = discord.utils.get(guild.roles, name=self.Role_name)
                try:
                    member = await guild.fetch_member(int(i['userid']))
                    await member.add_roles(role)
                except:
                    pass
            ListToSend.clear()

            if (Data.time == 1) or (Data.time >= int(self.Backup_every) / 3):
               
                print("Creating backup...")

                server_settings = {}

                server_settings['name'] = guild.name
                server_settings['icon_url'] = str(guild.icon)

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
                        async for message in channel.history(limit=self.Backup_message_count):
                            history.append({
                                "content": message.content,
                                "timestamp": message.created_at.isoformat(),
                                "author": {
                                    "id": message.author.id,
                                    "name": message.author.name,
                                }
                            })

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

        @self.bot.event
        async def on_ready():
            os.system("cls")
            print("Bot started")
            MemberSec.start()

        self.bot.run(self.BotToken)


class ApiBot:
    def __init__(self) -> None:
        self.RunApi()

    def RunApi(self):
        app = Flask(__name__)

        @app.route('/auth')
        def auth():
            code = request.args.get("code")

            if (code != None):
                if AntiSql(code) == True:
                    return jsonify({"error": "1004"})

                discord = Discordx()
                res = discord.ExchangeCode(code)
                try:
                    access_token = res['access_token']
                    refresh_token = res['refresh_token']
                    info = discord.GetInfo(access_token)
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

                if Memberdb.CheckIfUserIsInDb(data) == False:
                    Memberdb.AddNewMember(data)

                ListToSend.append(data)
                return "<script>window.close();</script>"
            else:
                return jsonify({"error": "1002"})

        waitress.serve(app, host="0.0.0.0", port=80)


if __name__ == "__main__":
    threading.Thread(target=ApiBot).start()
    Tools().discordbot()
