# main.py
import os
import logging
import json
import sqlite3
from datetime import datetime
import random
import threading

from dotenv import load_dotenv

# Discord imports
import discord
from discord.ext import commands, tasks
from discord.ui import View, TextInput, Modal, Select, Button

# Flask imports
from flask import Flask

# ---- Logging ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("discord_flask_app")

# ---- Load env ----
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

# ---- Database class (sqlite) ----
class Database:
    def __init__(self, path="discord_bot_pro.db"):
        self.db_path = path
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Basic required tables (same as before)
        c.execute("""
            CREATE TABLE IF NOT EXISTS guilds (
                id INTEGER PRIMARY KEY,
                name TEXT,
                prefix TEXT DEFAULT '!',
                welcome_channel INTEGER,
                welcome_message TEXT,
                goodbye_message TEXT,
                auto_role INTEGER,
                mod_log_channel INTEGER,
                level_system_enabled INTEGER DEFAULT 1,
                economy_enabled INTEGER DEFAULT 1,
                auto_mod_enabled INTEGER DEFAULT 1,
                music_enabled INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER,
                guild_id INTEGER,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                coins INTEGER DEFAULT 100,
                last_message TEXT,
                warnings INTEGER DEFAULT 0,
                reputation INTEGER DEFAULT 0,
                created_at TEXT,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                channel_id INTEGER,
                category_id INTEGER,
                status TEXT DEFAULT 'open',
                created_at TEXT,
                closed_at TEXT
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Database initialized/checked at %s", self.db_path)

    def get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

db = Database()

# ---- Bot configuration object ----
class BotConfig:
    def __init__(self):
        self.prefix = "!"
        self.version = "2.0.0"
        self.description = "Professional Discord Bot - Like MEE6 but Better!"
        self.owner_ids = []

    def load_config(self):
        try:
            os.makedirs("config", exist_ok=True)
            with open("config/config.json", "r") as f:
                cfg = json.load(f)
                self.__dict__.update(cfg)
        except FileNotFoundError:
            self.save_config()

    def save_config(self):
        os.makedirs("config", exist_ok=True)
        with open("config/config.json", "w") as f:
            json.dump(self.__dict__, f, indent=4)

config = BotConfig()
config.load_config()

# ---- Discord Bot ----
intents = discord.Intents.all()
def get_prefix_callable(bot, message):
    # placeholder; will be replaced by ProDiscordBot.get_prefix method which uses DB
    return commands.when_mentioned_or("!")(bot, message)

class ProDiscordBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            description=config.description,
            owner_ids=set(config.owner_ids)
        )
        self.launch_time = datetime.utcnow()
        self.command_stats = {}
        self.music_players = {}

    async def get_prefix(self, message):
        if not message.guild:
            return commands.when_mentioned_or("!")(self, message)
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT prefix FROM guilds WHERE id = ?", (message.guild.id,))
        result = c.fetchone()
        conn.close()
        prefix = result[0] if result else "!"
        return commands.when_mentioned_or(prefix)(self, message)

    async def setup_hook(self):
        # sync application commands (slash)
        try:
            await self.tree.sync()
            logger.info("Slash commands synced!")
        except Exception as e:
            logger.warning("Failed to sync tree: %s", e)

bot = ProDiscordBot()

# ---- UI Views (cleaned strings) ----
class MainMenuView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="🎮 Choose a feature to explore...",
        options=[
            discord.SelectOption(label="🛡️ Moderation", description="Kick, ban, warn, and more", emoji="🛡️"),
            discord.SelectOption(label="🎵 Music", description="Play music in voice channels", emoji="🎵"),
            discord.SelectOption(label="💰 Economy", description="Coins, shop, and inventory", emoji="💰"),
            discord.SelectOption(label="📊 Leveling", description="XP system and leaderboards", emoji="📊"),
            discord.SelectOption(label="🎫 Tickets", description="Support ticket system", emoji="🎫"),
            discord.SelectOption(label="⚙️ Settings", description="Configure server settings", emoji="⚙️"),
        ]
    )
    async def menu_select(self, interaction: discord.Interaction, select: Select):
        selection = select.values[0]

        if selection == "🛡️ Moderation":
            embed = discord.Embed(
                title="🛡️ Moderation System",
                description="Professional moderation tools at your fingertips!",
                color=0xff6b6b
            )
            embed.add_field(
                name="Commands",
                value=(
                    "• `/kick` - Remove member from server\n"
                    "• `/ban` - Permanently ban member\n"
                    "• `/warn` - Issue warning\n"
                    "• `/mute` - Temporarily mute member\n"
                    "• `/purge` - Delete multiple messages\n"
                    "• `/warnings` - View user warnings"
                ),
                inline=False
            )
            embed.add_field(
                name="Auto-Moderation",
                value=(
                    "• Spam protection\n"
                    "• Link filtering\n"
                    "• Bad word detection\n"
                    "• Raid protection"
                ),
                inline=False
            )

        elif selection == "🎵 Music":
            embed = discord.Embed(
                title="🎵 Music System",
                description="High-quality music streaming for your server!",
                color=0x4ecdc4
            )
            embed.add_field(
                name="Commands",
                value=(
                    "• `/play` - Play a song\n"
                    "• `/queue` - View music queue\n"
                    "• `/skip` - Skip current song\n"
                    "• `/pause/resume` - Control playback\n"
                    "• `/volume` - Adjust volume\n"
                    "• `/lyrics` - Get song lyrics"
                ),
                inline=False
            )

        elif selection == "💰 Economy":
            embed = discord.Embed(
                title="💰 Economy System",
                description="Virtual currency and shop system!",
                color=0xf7dc6f
            )
            embed.add_field(
                name="Commands",
                value=(
                    "• `/balance` - Check your coins\n"
                    "• `/daily` - Claim daily reward\n"
                    "• `/shop` - Browse server shop\n"
                    "• `/buy` - Purchase items\n"
                    "• `/inventory` - View your items\n"
                    "• `/pay` - Transfer coins"
                ),
                inline=False
            )

        elif selection == "📊 Leveling":
            embed = discord.Embed(
                title="📊 Leveling System",
                description="XP and ranking system to keep members engaged!",
                color=0xbb8fce
            )
            embed.add_field(
                name="Commands",
                value=(
                    "• `/rank` - View your rank card\n"
                    "• `/leaderboard` - Top server members\n"
                    "• `/setlevel` - Set user level (mods)\n"
                    "• `/rewards` - Level rewards"
                ),
                inline=False
            )

        elif selection == "🎫 Tickets":
            embed = discord.Embed(
                title="🎫 Ticket System",
                description="Professional support ticket system!",
                color=0x85c1e9
            )
            embed.add_field(
                name="Features",
                value=(
                    "• Create private support channels\n"
                    "• Automatic ticket logging\n"
                    "• Customizable categories\n"
                    "• Staff management tools"
                ),
                inline=False
            )

        elif selection == "⚙️ Settings":
            embed = discord.Embed(
                title="⚙️ Server Settings",
                description="Configure all bot features for your server!",
                color=0xa6acaf
            )
            embed.add_field(
                name="Configuration",
                value=(
                    "• Welcome/goodbye messages\n"
                    "• Auto-roles\n"
                    "• Moderation settings\n"
                    "• Feature toggles\n"
                    "• Prefix customization"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

class PlayMusicModal(Modal):
    def __init__(self):
        super().__init__(title="🎵 Play Music")
        self.song_input = TextInput(
            label="Song Name or URL",
            placeholder="Enter a YouTube URL or search term...",
            required=True,
            max_length=500
        )
        self.add_item(self.song_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            await interaction.response.send_message("❌ You need to be in a voice channel!", ephemeral=True)
            return
        await interaction.response.send_message(f"🎵 Searching for: `{self.song_input.value}`", ephemeral=True)

# ---- Events & commands ----
@bot.event
async def on_ready():
    logger.info("%s has connected to Discord!", bot.user)
    try:
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(bot.guilds)} servers | /help"
            ),
            status=discord.Status.online
        )
    except Exception:
        pass
    update_stats.start()

@bot.event
async def on_guild_join(guild):
    logger.info("Joined new guild: %s (%s)", guild.name, guild.id)
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO guilds (id, name, created_at) VALUES (?, ?, ?)",
              (guild.id, guild.name, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    # Simple XP addition
    if message.guild:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT last_message, xp, level FROM users WHERE user_id = ? AND guild_id = ?",
                  (message.author.id, message.guild.id))
        row = c.fetchone()
        can_gain_xp = True
        if row and row[0]:
            last = row[0]
            try:
                last_dt = datetime.fromisoformat(last)
                if (datetime.utcnow() - last_dt).seconds < 60:
                    can_gain_xp = False
            except Exception:
                can_gain_xp = True
        if can_gain_xp:
            xp_gain = random.randint(10, 25)
            c.execute("""
                INSERT OR REPLACE INTO users (user_id, guild_id, xp, last_message, created_at)
                VALUES (?, ?, COALESCE((SELECT xp FROM users WHERE user_id = ? AND guild_id = ?), 0) + ?, ?, COALESCE((SELECT created_at FROM users WHERE user_id = ? AND guild_id = ?), ?))
            """, (message.author.id, message.guild.id, message.author.id, message.guild.id, xp_gain, datetime.utcnow().isoformat(), message.author.id, message.guild.id, datetime.utcnow().isoformat()))
            conn.commit()
        conn.close()
    await bot.process_commands(message)

@bot.hybrid_command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="🤖 Professional Discord Bot",
        description="A feature-rich bot with everything your server needs!",
        color=0x3498db
    )
    embed.add_field(name="🛡️ Moderation", value="`/kick` `/ban` `/warn` `/mute` `/purge`", inline=True)
    embed.add_field(name="🎵 Music", value="`/play` `/queue` `/skip` `/pause` `/volume`", inline=True)
    embed.add_field(name="💰 Economy", value="`/balance` `/daily` `/shop` `/buy` `/pay`", inline=True)
    embed.add_field(name="📊 Leveling", value="`/rank` `/leaderboard` `/setlevel`", inline=True)
    embed.add_field(name="🎫 Tickets", value="`/ticket` `/close` `/add` `/remove`", inline=True)
    embed.set_footer(text=f"Bot Version {config.version}")
    await ctx.send(embed=embed, view=MainMenuView())

@tasks.loop(minutes=5)
async def update_stats():
    guild_count = len(bot.guilds)
    user_count = sum(g.member_count for g in bot.guilds) if bot.guilds else 0
    try:
        await bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name=f"{guild_count} servers | {user_count:,} users")
        )
    except Exception:
        pass

# ---- Flask app ----
flask_app = Flask(__name__)
flask_app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET", "please-change-this")
flask_app.config['DATABASE'] = db.db_path

@flask_app.route("/")
def dashboard():
    # Lightweight dashboard landing page
    return "<h2>Discord Bot Dashboard</h2><p>Bot is running.</p>"

def run_flask():
    logger.info("Starting Flask on port %s", PORT)
    flask_app.run(host="0.0.0.0", port=PORT, threaded=True)

# ---- Startup ----
def start_all():
    # Start flask in a background thread, then run the bot
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask thread started.")

    if not DISCORD_TOKEN:
        logger.error("DISCORD_BOT_TOKEN not set in environment. Exiting.")
        return

    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.exception("Bot failed to start: %s", e)

if __name__ == "__main__":
    start_all()
