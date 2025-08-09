from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Guild(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    prefix = db.Column(db.String(10), default='!')
    welcome_channel_id = db.Column(db.Integer)
    welcome_message = db.Column(db.Text)
    goodbye_message = db.Column(db.Text)
    auto_role_id = db.Column(db.Integer)

class ModLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guild_id = db.Column(db.Integer)
    moderator_id = db.Column(db.Integer)
    target_id = db.Column(db.Integer)
    action = db.Column(db.String(50))
    reason = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Warning(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guild_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    moderator_id = db.Column(db.Integer)
    reason = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class BotStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_online = db.Column(db.Boolean, default=False)
    guild_count = db.Column(db.Integer, default=0)
    user_count = db.Column(db.Integer, default=0)
    last_heartbeat = db.Column(db.DateTime, default=datetime.utcnow)
