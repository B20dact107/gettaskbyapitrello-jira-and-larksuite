from flask import Flask, request
from api.jira_service import jira_bp
#from api.larksuite_api import lark_bp
from api.larksuite_service import lark_bp
from api.trello_service import trello_bp
from dotenv import load_dotenv
import threading
from telegram_bot import run_bot  # Import service bot
from multiprocessing import Process 

load_dotenv()

app = Flask(__name__)
app.register_blueprint(jira_bp)
app.register_blueprint(lark_bp)
app.register_blueprint(trello_bp)

@app.route('/oauth/callback')
def lark_callback():
    code = request.args.get('code')
    print(f"🔑 Nhận được code từ Lark: {code}")
    return """
    <h1>Xác thực thành công!</h1>
    <p>Bạn có thể đóng trang này và quay lại Telegram bot</p>
    <script>window.close();</script>
    """
def run_flask():
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
if __name__ == '__main__':
    # Chạy Flask và bot Telegram trên 2 thread riêng
    flask_thread = threading.Thread(target=run_flask)
    bot_thread = threading.Thread(target=run_bot)
    
    flask_thread.start()
    bot_thread.start()
    
    flask_thread.join()
    bot_thread.join()
    