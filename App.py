from flask import Flask, render_template
from models import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///discord_bot_enhanced.db'
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def dashboard():
    return "Discord Bot Dashboard - Coming Soon!"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
