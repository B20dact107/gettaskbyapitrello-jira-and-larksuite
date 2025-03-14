from flask import Flask
from api.jira_service import jira_bp
#from api.larksuite_api import lark_bp
from api.larksuite_service import lark_bp
from api.trello_service import trello_bp
from dotenv import load_dotenv
import threading
from api.telegram_bot import run_bot  # Import service bot

load_dotenv()

app = Flask(__name__)
app.register_blueprint(jira_bp)
app.register_blueprint(lark_bp)
app.register_blueprint(trello_bp)

def run_flask():
    app.run(debug=True, use_reloader=False)
def run_telegram_bot():
    from api.telegram_bot import run_bot
    run_bot()

if __name__ == '__main__':
    # Chạy Flask và bot Telegram trên 2 thread riêng
    flask_thread = threading.Thread(target=run_flask)
    bot_thread = threading.Thread(target=run_telegram_bot)
    
    flask_thread.start()
    bot_thread.start()
    
    flask_thread.join()
    bot_thread.join()