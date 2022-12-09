# Backup Cord

Easy to setup discord bot for restoring members

Made By oxyn <3

# Setup (Windows server)

 Reinstall python libs
```bash
pip uninstall discord.py
pip install --force-reinstall discord.py-message-components
```
 Open config.json
![](https://raw.githubusercontent.com/OxynDev/Backup-Cord/main/temp/config-1.png)

Go to discord developers portal and create bot on new discord alt account [Discord Developers Applications](https://discord.com/developers/applications).

- Copy bot token and put in BOT_TOKEN
- Copy client id and put in CLIENT_ID
- Copy client secret and put in CLIENT_SEC
- Create secret password and put in PASSWORD (Password for member restore command)
- Copy server ip or domain and add `:8060/auth` (fe: http://something.wtf:8060/auth) put in REDIRECT_URL
- Add your url to Redirects on discord dev panel

![](https://raw.githubusercontent.com/OxynDev/Backup-Cord/main/temp/discord-dev-2.png)


Do this shit

![](https://raw.githubusercontent.com/OxynDev/Backup-Cord/main/temp/discord-dev-1.png)

Invite Bot to your server

- Copy server id and put in SERVER_ID
- Create channel for logs, copy channel id and put in LOG_CHANNEL
- Create role for verified members and put role name in ROLE_NAME


Download [XAMPP](https://www.apachefriends.org/pl/download.html)
 ---
 Now we need create database
 
Open XAMPP and run  apache and mysql server

![](https://raw.githubusercontent.com/OxynDev/Backup-Cord/main/temp/xampp-1.png)

- Open local [phpmyadmin](http://localhost/phpmyadmin) panel and create database named `backupbot`
- Create table named  `members`

![](https://raw.githubusercontent.com/OxynDev/Backup-Cord/main/temp/phpma-1.png)

- Create column named  `id` - int(11) AUTO_INCREMENT
- Create column named  `json` - text

![](https://raw.githubusercontent.com/OxynDev/Backup-Cord/main/temp/phpma-2.png)

Run discord bot and install all other libs
---
### Commands
- `.message`
 Command to send verify message

- `.backup <password>`
 Command to restore members (write on privat chat in new server)

---
### Question or problem? write dm oxyn#3520
