from flask import Flask
from service.jira_service import jira_bp
#from api.larksuite_api import lark_bp
from service.larksuite_service import lark_bp
from service.trello_service import trello_bp
from dotenv import load_dotenv
import threading
from service.telegram_bot import run_bot  # Import service bot
import logging
load_dotenv()

app = Flask(__name__)
app.register_blueprint(jira_bp)
app.register_blueprint(lark_bp)
app.register_blueprint(trello_bp)

def run_flask():
    logging.info("Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)  # Thêm host và port
    logging.info("Flask server started successfully.")


if __name__ == '__main__':
    # Chạy Flask và bot Telegram trên 2 thread riêng
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    logging.info("Flask server thread started.")
    logging.info("Telegram bot thread started.")
    run_bot()
    