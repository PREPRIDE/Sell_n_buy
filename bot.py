import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select, Modal, TextInput
import os
import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging
import aiohttp
import youtube_dl
from collections import defaultdict
import random
import asyncpg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Enhanced Bot Configuration
class BotConfig:
    def __init__(self):
        self.prefix = "!"
        self.version = "2.0.0"
        self.description = "Professional Discord Bot - Like MEE6 but Better!"
        self.owner_ids = []
        
    def load_config(self):
        try:
            with open('config/config.json', 'r') as f:
                config = json.load(f)
                self.__dict__.update(config)
        except FileNotFoundError:
            self.save_config()
    
    def save_config(self):
        os.makedirs('config', exist_ok=True)
        with open('config/config.json', 'w') as f:
            json.dump(self.__dict__, f, indent=4)

config = BotConfig()
config.load_config()

# Enhanced Database with all features
class Database:
    def __init__(self):
        self.db_path = "discord_bot_pro.db"
        self.init_database()
    
    def init_database(self):
        """Initialize all database tables"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Guilds table (server settings)
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
        
        # Users table (global user data)
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
        
        # Moderation logs
        c.execute("""
            CREATE TABLE IF NOT EXISTS mod_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                action TEXT,
                reason TEXT,
                duration INTEGER,
                timestamp TEXT
            )
        """)
        
        # Custom commands
        c.execute("""
            CREATE TABLE IF NOT EXISTS custom_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                name TEXT,
                response TEXT,
                created_by INTEGER,
                created_at TEXT
            )
        """)
        
        # Economy items/shop
        c.execute("""
            CREATE TABLE IF NOT EXISTS shop_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                name TEXT,
                price INTEGER,
                description TEXT,
                role_id INTEGER,
                stock INTEGER DEFAULT -1
            )
        """)
        
        # User inventory
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_inventory (
                user_id INTEGER,
                guild_id INTEGER,
                item_id INTEGER,
                quantity INTEGER DEFAULT 1,
                purchased_at TEXT,
                PRIMARY KEY (user_id, guild_id, item_id)
            )
        """)
        
        # Tickets system
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
        
        # Reaction roles
        c.execute("""
            CREATE TABLE IF NOT EXISTS reaction_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                message_id INTEGER,
                channel_id INTEGER,
                emoji TEXT,
                role_id INTEGER
            )
        """)
        
        # Music queue
        c.execute("""
            CREATE TABLE IF NOT EXISTS music_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                title TEXT,
                url TEXT,
                requested_by INTEGER,
                duration INTEGER,
                added_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully!")
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)

# Initialize database
db = Database()

# Enhanced Bot Class
class ProDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()  # Full permissions
        
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            description=config.description,
            owner_ids=set(config.owner_ids)
        )
        
        self.launch_time = datetime.utcnow()
        self.command_stats = defaultdict(int)
        self.music_players = {}
        
    async def get_prefix(self, message):
        """Dynamic prefix per server"""
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
        """Load all cogs/extensions"""
        extensions = [
            'cogs.moderation',
            'cogs.music', 
            'cogs.economy',
            'cogs.leveling',
            'cogs.tickets'
        ]
        
        for ext in extensions:
            try:
                await self.load_extension(ext)
                logger.info(f"Loaded {ext}")
            except Exception as e:
                logger.error(f"Failed to load {ext}: {e}")
        
        await self.tree.sync()
        logger.info("Slash commands synced!")

bot = ProDiscordBot()

# Enhanced UI Components
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
                value='/kick'  # Corrected
• `/ban` - Permanently ban member
• `/warn` - Issue warning
• `/mute` - Temporarily mute member
• `/purge` - Delete multiple messages
• `/warnings` - View user warnings",
                inline=False
            )
            embed.add_field(
                name="Auto-Moderation",
                value="• Spam protection
• Link filtering
• Bad word detection
• Raid protection",
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
                value="• `/play` - Play a song
• `/queue` - View music queue
• `/skip` - Skip current song
• `/pause/resume` - Control playback
• `/volume` - Adjust volume
• `/lyrics` - Get song lyrics",
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
                value="• `/balance` - Check your coins
• `/daily` - Claim daily reward
• `/shop` - Browse server shop
• `/buy` - Purchase items
• `/inventory` - View your items
• `/pay` - Transfer coins",
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
                value="• `/rank` - View your rank card
• `/leaderboard` - Top server members
• `/setlevel` - Set user level (mods)
• `/rewards` - Level rewards",
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
                value="• Create private support channels
• Automatic ticket logging
• Customizable categories
• Staff management tools",
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
                value="• Welcome/goodbye messages
• Auto-roles
• Moderation settings
• Feature toggles
• Prefix customization",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class QuickActionsView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🎵 Play Music", style=discord.ButtonStyle.success, emoji="🎵")
    async def play_music(self, interaction: discord.Interaction, button: Button):
        modal = PlayMusicModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📊 Server Stats", style=discord.ButtonStyle.primary, emoji="📊")
    async def server_stats(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        
        # Get database stats
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users WHERE guild_id = ?", (guild.id,))
        active_users = c.fetchone()[0]
        conn.close()
        
        embed = discord.Embed(
            title=f"📊 {guild.name} Statistics",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="👥 Total Members", value=f"{guild.member_count:,}", inline=True)
        embed.add_field(name="🤖 Bots", value=f"{len([m for m in guild.members if m.bot]):,}", inline=True)
        embed.add_field(name="👨‍💻 Humans", value=f"{len([m for m in guild.members if not m.bot]):,}", inline=True)
        embed.add_field(name="📈 Active Users", value=f"{active_users:,}", inline=True)
        embed.add_field(name="💬 Text Channels", value=f"{len(guild.text_channels):,}", inline=True)
        embed.add_field(name="🔊 Voice Channels", value=f"{len(guild.voice_channels):,}", inline=True)
        embed.add_field(name="😎 Roles", value=f"{len(guild.roles):,}", inline=True)
        embed.add_field(name="😀 Emojis", value=f"{len(guild.emojis):,}", inline=True)
        embed.add_field(name="🎮 Boosts", value=f"{guild.premium_subscription_count:,}", inline=True)
        embed.add_field(name="📅 Created", value=guild.created_at.strftime("%B %d, %Y"), inline=False)
        
        if guild.owner:
            embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.secondary, emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        # Check if user already has an open ticket
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM tickets WHERE guild_id = ? AND user_id = ? AND status = 'open'", 
                 (interaction.guild_id, interaction.user.id))
        existing = c.fetchone()
        
        if existing:
            await interaction.response.send_message("❌ You already have an open ticket!", ephemeral=True)
            return
        
        # Create ticket channel
        category = discord.utils.get(interaction.guild.categories, name="🎫 TICKETS")
        if not category:
            category = await interaction.guild.create_category("🎫 TICKETS")
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel = await interaction.guild.create_text_channel(
            f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )
        
        # Save to database
        c.execute("INSERT INTO tickets (guild_id, user_id, channel_id, category_id, created_at) VALUES (?, ?, ?, ?, ?)",
                 (interaction.guild_id, interaction.user.id, channel.id, category.id, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="🎫 Ticket Created",
            description=f"Your support ticket has been created: {channel.mention}",
            color=0x2ecc71
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Send welcome message to ticket
        welcome_embed = discord.Embed(
            title="🎫 Support Ticket",
            description=f"Hello {interaction.user.mention}! Staff will be with you shortly.

Please describe your issue in detail.",
            color=0x3498db
        )
        await channel.send(embed=welcome_embed)

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
        # Music functionality would be handled by the music cog

# Enhanced Event Handlers
@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Connected to {len(bot.guilds)} guilds')
    logger.info(f'Serving {sum(guild.member_count for guild in bot.guilds)} users')
    
    # Set status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(bot.guilds)} servers | /help"
        ),
        status=discord.Status.online
    )
    
    # Start background tasks
    update_stats.start()

@bot.event
async def on_guild_join(guild):
    """Bot joins a new server"""
    logger.info(f"Joined new guild: {guild.name} ({guild.id})")
    
    # Add guild to database
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO guilds (id, name, created_at) VALUES (?, ?, ?)",
             (guild.id, guild.name, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    
    # Send welcome message
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="🎉 Thanks for adding me!",
                description=f"Hello **{guild.name}**! I'm a professional Discord bot with tons of features!",
                color=0x2ecc71
            )
            embed.add_field(
                name="🚀 Quick Start",
                value="• Use `/help` to see all commands
• Use `/setup` to configure me
• Visit the web dashboard for advanced settings",
                inline=False
            )
            embed.add_field(
                name="✨ Key Features",
                value="• Advanced Moderation
• Music Player
• Economy System
• Leveling & XP
• Ticket System
• And much more!",
                inline=False
            )
            embed.set_footer(text="Made with ❤️ for your server")
            
            await channel.send(embed=embed, view=MainMenuView())
            break

@bot.event
async def on_member_join(member):
    """Enhanced welcome system"""
    if member.bot:
        return
    
    conn = db.get_connection()
    c = conn.cursor()
    
    # Get guild settings
    c.execute("SELECT welcome_channel, welcome_message, auto_role FROM guilds WHERE id = ?", (member.guild.id,))
    settings = c.fetchone()
    
    # Add user to database
    c.execute("INSERT OR REPLACE INTO users (user_id, guild_id, created_at) VALUES (?, ?, ?)",
             (member.id, member.guild.id, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    
    if not settings:
        return
    
    welcome_channel_id, welcome_message, auto_role_id = settings
    
    # Send welcome message
    if welcome_channel_id:
        channel = bot.get_channel(welcome_channel_id)
        if channel:
            if welcome_message:
                message = welcome_message.format(
                    user=member.mention,
                    server=member.guild.name,
                    member_count=member.guild.member_count
                )
                await channel.send(message)
            else:
                embed = discord.Embed(
                    title="👋 Welcome!",
                    description=f"Welcome to **{member.guild.name}**, {member.mention}!",
                    color=0x2ecc71,
                    timestamp=datetime.utcnow()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.add_field(name="Member #", value=str(member.guild.member_count), inline=True)
                embed.add_field(name="Account Created", value=member.created_at.strftime("%B %d, %Y"), inline=True)
                embed.set_footer(text=f"ID: {member.id}")
                
                await channel.send(embed=embed, view=QuickActionsView())
    
    # Auto-role assignment
    if auto_role_id:
        role = member.guild.get_role(auto_role_id)
        if role:
            try:
                await member.add_roles(role, reason="Auto-role on join")
            except discord.Forbidden:
                logger.warning(f"Cannot assign auto-role in {member.guild.name}: Missing permissions")

@bot.event
async def on_message(message):
    """Enhanced message handling with XP and auto-moderation"""
    if message.author.bot:
        return
    
    # XP System
    if message.guild:
        conn = db.get_connection()
        c = conn.cursor()
        
        # Check if user can gain XP (cooldown system)
        c.execute("SELECT last_message FROM users WHERE user_id = ? AND guild_id = ?", 
                 (message.author.id, message.guild.id))
        result = c.fetchone()
        
        can_gain_xp = True
        if result and result[0]:
            last_message = datetime.fromisoformat(result[0])
            if (datetime.utcnow() - last_message).seconds < 60:  # 1 minute cooldown
                can_gain_xp = False
        
        if can_gain_xp:
            # Give random XP (15-25)
            xp_gain = random.randint(15, 25)
            
            c.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, guild_id, xp, last_message, created_at) 
                VALUES (?, ?, 
                    COALESCE((SELECT xp FROM users WHERE user_id = ? AND guild_id = ?), 0) + ?, 
                    ?, 
                    COALESCE((SELECT created_at FROM users WHERE user_id = ? AND guild_id = ?), ?))
            """, (message.author.id, message.guild.id, message.author.id, message.guild.id, 
                 xp_gain, datetime.utcnow().isoformat(), message.author.id, message.guild.id, 
                 datetime.utcnow().isoformat()))
            
            # Check for level up
            c.execute("SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?", 
                     (message.author.id, message.guild.id))
            user_data = c.fetchone()
            
            if user_data:
                current_xp, current_level = user_data
                required_xp = 5 * (current_level ** 2) + 50 * current_level + 100
                
                if current_xp >= required_xp:
                    new_level = current_level + 1
                    c.execute("UPDATE users SET level = ? WHERE user_id = ? AND guild_id = ?",
                             (new_level, message.author.id, message.guild.id))
                    
                    # Send level up message
                    embed = discord.Embed(
                        title="🎉 Level Up!",
                        description=f"{message.author.mention} reached **Level {new_level}**!",
                        color=0xf1c40f
                    )
                    embed.set_thumbnail(url=message.author.display_avatar.url)
                    await message.channel.send(embed=embed)
        
        conn.commit()
        conn.close()
    
    await bot.process_commands(message)

# Essential Commands
@bot.hybrid_command(name="help")
async def help_command(ctx):
    """Show the main help menu"""
    embed = discord.Embed(
        title="🤖 Professional Discord Bot",
        description="A feature-rich bot with everything your server needs!",
        color=0x3498db
    )
    embed.add_field(
        name="🛡️ Moderation",
        value="`/kick` `/ban` `/warn` `/mute` `/purge`",
        inline=True
    )
    embed.add_field(
        name="🎵 Music",
        value="`/play` `/queue` `/skip` `/pause` `/volume`",
        inline=True
    )
    embed.add_field(
        name="💰 Economy",
        value="`/balance` `/daily` `/shop` `/buy` `/pay`",
        inline=True
    )
    embed.add_field(
        name="📊 Leveling",
        value="`/rank` `/leaderboard` `/setlevel`",
        inline=True
    )
    embed.add_field(
        name="🎫 Tickets",
        value="`/ticket` `/close` `/add` `/remove`",
        inline=True
    )
    embed.add_field(
        name="⚙️ Admin",
        value="`/setup` `/config` `/prefix` `/autorole`",
        inline=True
    )
    embed.set_footer(text="Use the menu below for interactive help!")
    
    await ctx.send(embed=embed, view=MainMenuView())

@bot.hybrid_command(name="setup")
@commands.has_permissions(administrator=True)
async def setup_server(ctx):
    """Quick server setup wizard"""
    embed = discord.Embed(
        title="⚙️ Server Setup",
        description="Let's configure your server! Use the buttons below:",
        color=0xe74c3c
    )
    embed.add_field(
        name="📋 Setup Steps",
        value="1. Set welcome channel
2. Configure auto-role
3. Set moderation log channel
4. Enable features
5. Customize prefix",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name="stats")
async def bot_stats(ctx):
    """Show bot statistics"""
    uptime = datetime.utcnow() - bot.launch_time
    
    embed = discord.Embed(
        title="📊 Bot Statistics",
        color=0x9b59b6,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="🏠 Servers", value=f"{len(bot.guilds):,}", inline=True)
    embed.add_field(name="👥 Users", value=f"{sum(g.member_count for g in bot.guilds):,}", inline=True)
    embed.add_field(name="⏰ Uptime", value=f"{uptime.days}d {uptime.seconds//3600}h", inline=True)
    embed.add_field(name="🏓 Latency", value=f"{round(bot.latency*1000)}ms", inline=True)
    embed.add_field(name="🧠 Memory", value="Loading...", inline=True)
    embed.add_field(name="💻 Commands", value=f"{len(bot.commands)}", inline=True)
    embed.set_footer(text=f"Bot Version {config.version}")
    
    await ctx.send(embed=embed)

# Background tasks
@tasks.loop(minutes=5)
async def update_stats():
    """Update bot statistics and presence"""
    guild_count = len(bot.guilds)
    user_count = sum(guild.member_count for guild in bot.guilds)
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{guild_count} servers | {user_count:,} users"
        )
    )

# Error handling
@bot.event
async def on_command_error(ctx, error):
    """Enhanced error handling"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Missing Permissions",
            description="You don't have permission to use this command.",
            color=0xe74c3c
        )
        await ctx.send(embed=embed, ephemeral=True)
    elif isinstance(error, commands.BotMissingPermissions):
        embed = discord.Embed(
            title="❌ Bot Missing Permissions",
            description=f"I need the following permissions: {', '.join(error.missing_permissions)}",
            color=0xe74c3c
        )
        await ctx.send(embed=embed)
    else:
        logger.error(f"Unhandled error: {error}")
        embed = discord.Embed(
            title="❌ An Error Occurred",
            description="Something went wrong. The error has been logged.",
            color=0xe74c3c
        )
        await ctx.send(embed=embed)

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("No bot token found! Please set DISCORD_BOT_TOKEN in your .env file")
        exit(1)
    
    try:
        bot.run(token)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
