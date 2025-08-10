import os
import logging
from datetime import datetime
from threading import Threadimport discord
from discord.ext import commands, tasks
from flask import Flask, render_template_string
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenvEnv + loggingload_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("main")DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
SECRET_KEY = os.getenv("SECRET_KEY", "change-this")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///discord_bot_enhanced.db")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")if not DISCORD_BOT_TOKEN:
log.error("DISCORD_BOT_TOKEN missing. Add it to environment or .env")
raise SystemExit(1)Flask + DBapp = Flask(name)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)class Guild(db.Model):
id = db.Column(db.Integer, primary_key=True)
name = db.Column(db.String(100))
prefix = db.Column(db.String(10), default="!")
welcome_channel_id = db.Column(db.Integer)
welcome_message = db.Column(db.Text)
goodbye_message = db.Column(db.Text)
auto_role_id = db.Column(db.Integer)class ModLog(db.Model):
id = db.Column(db.Integer, primary_key=True)
guild_id = db.Column(db.Integer)
moderator_id = db.Column(db.Integer)
target_id = db.Column(db.Integer)
action = db.Column(db.String(50))
reason = db.Column(db.Text)
timestamp = db.Column(db.DateTime, default=datetime.utcnow)class Warning(db.Model):
id = db.Column(db.Integer, primary_key=True)
guild_id = db.Column(db.Integer)
user_id = db.Column(db.Integer)
moderator_id = db.Column(db.Integer)
reason = db.Column(db.Text)
active = db.Column(db.Boolean, default=True)
timestamp = db.Column(db.DateTime, default=datetime.utcnow)class BotStatus(db.Model):
id = db.Column(db.Integer, primary_key=True)
is_online = db.Column(db.Boolean, default=False)
guild_count = db.Column(db.Integer, default=0)
user_count = db.Column(db.Integer, default=0)
last_heartbeat = db.Column(db.DateTime, default=datetime.utcnow)DASHBOARD_HTML = """
@app.route("/")
def index():
with app.app_context():
status = BotStatus.query.first()
return render_template_string(DASHBOARD_HTML, status=status)def run_flask():
with app.app_context():
db.create_all()
if not BotStatus.query.first():
db.session.add(BotStatus(is_online=False, guild_count=0, user_count=0))
db.session.commit()
port = int(os.getenv("PORT", "5000"))
app.run(host=os.getenv("HOST", "0.0.0.0"), port=port)Discord botintents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = Trueclass Bot(commands.Bot):
def init(self):
super().init(command_prefix=BOT_PREFIX, intents=intents, help_command=None)
self.launch_time = datetime.utcnow()textasync def on_ready(self):
    log.info("Logged in as %s (%s)", self.user, self.user.id)
    await self.change_presence(activity=discord.Game(name=f"/help | {BOT_PREFIX}help"))
    update_stats.start()
    with app.app_context():
        status = BotStatus.query.first() or BotStatus()
        status.is_online = True
        status.guild_count = len(self.guilds)
        status.user_count = sum((g.member_count or 0) for g in self.guilds)
        status.last_heartbeat = datetime.utcnow()
        db.session.add(status)
        db.session.commit()

async def on_guild_join(self, guild: discord.Guild):
    with app.app_context():
        if not Guild.query.get(guild.id):
            db.session.add(Guild(id=guild.id, name=guild.name, prefix=BOT_PREFIX))
            db.session.commit()bot = Bot()@bot.command(name="help")
async def help_cmd(ctx):
embed = discord.Embed(
title="Help",
description=f"Prefix: {BOT_PREFIX}\nCommands: {BOT_PREFIX}help, {BOT_PREFIX}ping",
color=0x3498db
)
await ctx.reply(embed=embed)@bot.command()
async def ping(ctx):
await ctx.reply(f"Pong! {round(bot.latency*1000)}ms")@tasks.loop(minutes=5)
async def update_stats():
with app.app_context():
status = BotStatus.query.first() or BotStatus()
status.guild_count = len(bot.guilds)
status.user_count = sum((g.member_count or 0) for g in bot.guilds)
status.last_heartbeat = datetime.utcnow()
db.session.add(status)
db.session.commit()def main():
Thread(target=run_flask, daemon=True).start()
try:
bot.run(DISCORD_BOT_TOKEN)
finally:
with app.app_context():
status = BotStatus.query.first()
if status:
status.is_online = False
status.last_heartbeat = datetime.utcnow()
db.session.commit()if name == "main":
main()
