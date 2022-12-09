import threading, json, tracemalloc, httpx
from dotenv import load_dotenv
import mysql.connector
from requests.api import request

# DISCORD LIBS
import discord, discord.ext 
from discord.ext import commands, tasks
from discord import Button, ButtonStyle, ActionRow
from discord.ext.commands import has_permissions
from discord.utils import get

# FLASK
from flask import Flask, redirect, request, jsonify
import waitress


def AntiSql(string):
    sqlblacklist = list("'[]{},./?=-|)(*^")
    if any(ext in string for ext in sqlblacklist):
        return True

load_dotenv()
tracemalloc.start()
event=threading.Event()

config = json.loads(open("config.json","r").read())

class Error(Exception):
    pass

class MembersDb:
    def __init__(self) -> None:
        self.DataBase = mysql.connector.connect(user='root', password='',host='localhost',database='backupbot')
        self.Cursor = self.DataBase.cursor()
        
    def GetMembers(self):     
        self.Cursor.execute('SELECT id, json FROM members')

        records = self.Cursor.fetchall()
        if records == []:
            return 1001 
        return list(records)

    def AddNewMember(self,jsonx):
        self.Cursor.execute("insert into members (id, json) values (default, '"+json.dumps(jsonx)+"');")
        self.DataBase.commit()

    def UpdateMember(self, json0, json1):
        self.Cursor.execute("UPDATE members SET json = '"+json0+"' WHERE json = '"+json1+"'")
        self.DataBase.commit()

    def CheckIfUserIsInDb(self,jsonx):
        self.Cursor.execute("SELECT json FROM members WHERE json='{0}'".format(json.dumps(jsonx)))
        records = self.Cursor.fetchall()
        if records == []:
            return False 
        else:
            return records

Memberdb = MembersDb()

class Discordx:
    def __init__(self) -> None:

        self.BotToken = config['BOT_TOKEN']
        self.ServerId = config['SERVER_ID']
        self.client_id = config['CLIENT_ID']
        self.client_sec = config['CLIENT_SEC']
        self.redirect_url = config['REDIRECT_URL']

    def ExchangeCode(self, code):


        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'client_id':self.client_id,'client_secret': self.client_sec,'grant_type': 'authorization_code','code': code,'redirect_uri': self.redirect_url,
        #'scope': "identify guilds guilds.join"
        }
        r = httpx.post(f"https://discord.com/api/v9/oauth2/token",data=data,headers=headers)
        return r.json()

    def GetInfo(self, code):
        headers = {'Authorization': 'Bearer ' + code,}
        response = httpx.get("https://discord.com/api/v9/users/@me", headers=headers)
        return response.json()

    def GetNewToken(self, token):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_sec,
            'grant_type': 'refresh_token',
            'refresh_token': token
        }
        r = httpx.post("https://discord.com/api/v9/oauth2/token",data=data,headers=headers)
        return r.json()

    def AddToGuild(self, access_token, user_id, guild_id):

        headers = {
            "Authorization" : f"Bot {self.BotToken}",
            'Content-Type': 'application/json'
        }

        data = {"access_token": access_token}

        url=f"https://discordapp.com/api/v9/guilds/{guild_id}/members/{user_id}"
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
        self.client_id = config['CLIENT_ID']
        self.client_sec = config['CLIENT_SEC']
        self.log_channel = config['LOG_CHANNEL']
        self.role_name = config['ROLE_NAME']
        self.password = config['PASSWORD']
        self.redirect_url = config['REDIRECT_URL']
        

    def discordbot(self):

        self.bot = commands.Bot(command_prefix=".", help_command=None, intents=discord.Intents().all(),activity=discord.Game(name="BackupCord"))

        @tasks.loop(seconds = 3)
        async def myLoop():
            for i in ListToSend:
                membercount = str(len(Memberdb.GetMembers()))
                channel = discord.utils.get(self.bot.get_all_channels(), id=int(self.log_channel))
                embed = discord.Embed(title='', description="""
**✅ | Member verified**

≡ | User: <@{0}>
≡ | Ip: `{1}`

≡ | Member in db: `{2}`
""".format(i['userid'],i['ip'],membercount), color=5763719)
                await channel.send(embed=embed)

                guild = self.bot.get_guild(int(self.ServerId))
                role = get(guild.roles, name=self.role_name)
                try:
                    await get(self.bot.get_all_members(), id=int(i['userid'])).add_roles(role)
                except:
                    pass
            ListToSend.clear()

        @self.bot.command()
        async def message(ctx):
            components = [ActionRow((Button(url='https://discord.com/oauth2/authorize?response_type=code&client_id='+self.client_id+'&scope=identify+guilds.join&redirect_uri='+self.redirect_url,label="",style=ButtonStyle.url,emoji='✅')))]
            embed = discord.Embed(title='', description='__**Verification**__', color=5763719)
            await ctx.message.channel.send(embed=embed, components=components)

        
        @self.bot.command()
        @has_permissions(administrator=True)
        async def backup(ctx,arg):
            if arg == self.password:
                members = Memberdb.GetMembers()
                global added; added = 0
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

        myLoop.start()
        threading.Thread(target=self.bot.run,args=(self.BotToken,)).start()


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
                    return jsonify({"error":"1004"})

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
                    return jsonify({"error":"1005"})
                data = {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "username":username,
                    "avatar":avatar,
                    "userid":userid,
                    "ip":request.remote_addr
                }
                
                if Memberdb.CheckIfUserIsInDb(data) == False:
                    Memberdb.AddNewMember(data)

                ListToSend.append(data)
                return "<script>window.close();</script>"
            else:
                return jsonify({"error":"1002"})

        waitress.serve(app,host="0.0.0.0",port=8060)




if __name__ == "__main__":
    threading.Thread(target=ApiBot).start()
    Tools().discordbot()
