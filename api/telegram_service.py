import os
import requests
from requests.auth import HTTPBasicAuth
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.ext import ConversationHandler, CallbackQueryHandler  
from pymongo import MongoClient
from dotenv import load_dotenv
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta  

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db= client["task_database"]
tasks_collection = db ["unified_tasks"]
users_collection = db["users"]  
user_credentials = db["user_credentials"]


# Thêm phần định nghĩa state ở đầu file
(AWAITING_TRELLO_CREDS, AWAITING_JIRA_CREDS, AWAITING_LARK_CODE, PLATFORM_SELECTED) = range(4, 8)


TOKEN = os.getenv("TELEGRAM_TOKEN")

async def check_trello_auth(user_id: int) -> bool:
    creds = user_credentials.find_one({
        "user_id": user_id,
        "platform": "trello"
    })
    return creds is not None and "default_board" in creds and "default_list" in creds

async def create_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = users_collection.find_one({"chat_id": update.message.chat_id})
    if not user:
        await update.message.reply_text("❌ Vui lòng dùng /start trước!")
        return ConversationHandler.END
    
    if not await check_trello_auth(user["user_id"]):
        await update.message.reply_text(
            "⚠️ Vui lòng kết nối Trello trước!\n"
            "Dùng lệnh /connect và chọn Trello để kết nối"
        )
        return ConversationHandler.END
    
    await update.message.reply_text("📝 Hãy nhập tiêu đề task:")
    return DESCRIPTION


async def handle_trello_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.split(":")
        if len(parts) != 4:
            raise ValueError("Sai định dạng")
            
        api_key, token, board_id, list_id = parts
        
        user_credentials.update_one(
            {"user_id": update.message.from_user.id, "platform": "trello"},
            {"$set": {
                "api_key": api_key,
                "token": token,
                "default_board": board_id,
                "default_list": list_id,
                "connected_at": datetime.now()
            }},
            upsert=True
        )
        
        await update.message.reply_text("✅ Kết nối Trello thành công!")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return ConversationHandler.END
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Đã hủy thao tác!")
    context.user_data.clear()
    return ConversationHandler.END

(
    PLATFORM_SELECTED,
    AWAITING_TRELLO_BOARD_NAME,
    AWAITING_TRELLO_LIST_NAME,
    AWAITING_JIRA_PROJECT_KEY
) = range(4, 8)  


async def handle_platform_connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  
    platform = query.data.split("_")[1]
    
    if platform == "trello":
        return await handle_trello_connection(update, context)
    elif platform == "jira":
        return await handle_jira_connection(update, context)
    # elif platform == "lark":
    #     return await handle_lark_connection(update, context)
    else:
        await query.answer("Nền tảng không hỗ trợ!")
        return ConversationHandler.END

async def start(update : Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    # Lưu thông tin người dùng vào collection 'users'
    db.users.update_one(
        {"user_id": user.id},
        {"$set": {
            "username": user.username,
            "chat_id": update.message.chat_id
        }},
        upsert=True
    )
    await update.message.reply_text(
        "👋 Chào mừng đến với Assistant AI Bot!\n"
        "Các lệnh hỗ trợ:\n"
        "/start - Hướng dẫn sử dụng\n"
        "/username - [user_name] Thiết lập tên người dùng\n"
        "/tasks - Hiển thị danh sách task (dùng user_id nếu cung cấp, "
        "nếu không thì dùng chat_id)\n"
        "/create_issue [nội dung] - Tạo task mới\n"
        "⚠️ Cảnh báo tự động sẽ được gửi khi task sắp hết hạn!"
    )
async def username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Vui lòng nhập username (ví dụ: /username lamdao)")
        return
    
    new_username = context.args[0]
    user = update.message.from_user
    
    users_collection.update_one(
        {"user_id": user.id},
        {"$set": {"username": new_username}},
        upsert=True
    )
    
    await update.message.reply_text(f"✅ Đã cập nhật username thành: {new_username}")
async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = users_collection.find_one({"chat_id": update.message.chat_id})
    
    if not user:
        await update.message.reply_text("❌ Vui lòng dùng /start trước!")
        return
    
    # Tìm các task liên quan
    tasks = tasks_collection.find({
        "$or": [
            {"members": user["username"]},
            {"assignees": user["username"]}
        ]
    }, {"_id": 0})
    
    if not tasks:
        await update.message.reply_text("📭 Bạn không có task nào!")
        return
    
    response = "📋 Danh sách task của bạn:\n"
    for task in tasks:
        response += f"- {task['title']} (Deadline: {task['due_date']})\n"
    await update.message.reply_text(response)

TITLE, DESCRIPTION, PRIORITY, ASSIGNEES, PLATFORM = range(5)

async def create_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Hãy nhập tiêu đề task:")
    return TITLE

async def get_title(update: Update , context: ContextTypes.DEFAULT_TYPE):
    context.user_data['title'] = update.message.text  
    await update.message.reply_text("📄 Nhập mô tả task:")
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("🔝 Chọn độ ưu tiên (low/medium/high")
    return PRIORITY

async def get_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['priority'] = update.message.text
    await update.message.reply_text("👥 Nhập user_name assignees (cách nhau bằng dấu phẩy):")
    return ASSIGNEES

async def get_assignees(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assignees = [name.strip() for name in update.message.text.split(",")]
    context.user_data['assignees'] = assignees
    await update.message.reply_text("🌐 Nhập nền tảng (trello, jira, lark):")
    return PLATFORM

async def get_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['platform'] = update.message.text.strip().lower()
    
    try:
        # Gọi hàm xử lý cuối cùng
        await finalize_task(update, context)
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return ConversationHandler.END
async def create_task_on_platform(platform: str, task_data: dict):
    if platform == "trello":
        try:
            # Lấy thông tin xác thực từ database
            creds = user_credentials.find_one({
                "user_id": task_data["user_id"],
                "platform": "trello"
            })
            
            if not creds:
                raise Exception("Chưa kết nối Trello! Vui lòng dùng lệnh /connect trước")
            # Lấy member IDs từ Trello
            member_ids = []
            for username in task_data.get("assignees", []):
                # Gọi API để lấy thông tin thành viên
                members_url = f"https://api.trello.com/1/boards/{creds['default_board']}/members"
                params = {
                    'key': creds['api_key'],
                    'token': creds['token'],
                    'filter': 'all'
                }
                response = requests.get(members_url, params=params)
                
                if response.status_code == 200:
                    for member in response.json():
                        if member['username'] == username:
                            member_ids.append(member['id'])
                            break

                
            # Chuẩn bị API endpoint và params
            url = "https://api.trello.com/1/cards"
            query = {
                'key': creds["api_key"],
                'token': creds["token"],
                'idList': creds["default_list"],
                'name': task_data["title"],
                'description': task_data.get("description", ""),
                'due': task_data.get("due_date"),
                'idMembers': ",".join(member_ids) if member_ids else "",
                'pos': 'top'
            }
            
            # Gọi API Trello
            response = requests.post(
                url,
                params=query,
                timeout=10
            )
            
            if response.status_code != 200:
                raise Exception(f"Lỗi Trello ({response.status_code}): {response.text}")
                
            card_id = response.json()["id"]
            print(f"a nhô")
            return card_id
            
        except Exception as e:
            raise Exception(f"Không thể tạo task trên Trello: {str(e)}")
        
    
    if platform == "jira":
        try:

            if not all([os.getenv("JIRA_DOMAIN"), os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN")]):
                raise Exception("Thiếu cấu hình Jira trong .env!")
            
            url = f"https://{os.getenv('JIRA_DOMAIN')}/rest/api/3/issue"

            adf_description = convert_text_to_adf(task_data.get("description", ""))
            username_input = task_data.get("assignees", [""])[0]
            if not username_input:
                account_id = None
            else:
                account_id = get_jira_account_id_from_username(username_input)
        
            
            # Chuẩn bị payload
            payload = {
                "fields": {
                    "project": {"key": os.getenv("JIRA_PROJECT_KEY")},
                    "issuetype": {"name": "Task"},  
                    "summary": task_data["title"],
                    "description": adf_description,
                    "assignee": {"accountId": account_id} if account_id else None
                    
                }
            }
            
            # Gọi API Jira
            response = requests.post(
                url,
                auth=HTTPBasicAuth(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN")),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                json=payload,
                timeout=10
            )
            
            # Debug: In response ra console
            print("Jira API Response:", response.status_code)
            print("Response Text:", response.text)
            
            if response.status_code == 201:
                return response.json().get("id")
            else:
                raise Exception(f"Jira API Error ({response.status_code}): {response.text}")
        
        except Exception as e:
            raise Exception(f"Không thể tạo task trên Jira: {str(e)}")
    
    
    elif platform == "lark":
        print(f"a nhô 1 2 3 4")

def get_jira_account_id_from_username(username: str) -> str:
    url = f"https://{os.getenv('JIRA_DOMAIN')}/rest/api/3/user/search"
    auth = HTTPBasicAuth(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))
    params = {"query": username}
    response = requests.get(url, params=params, auth=auth, headers={"Accept": "application/json"})
    
    if response.status_code != 200 or not response.json():
        raise Exception(f"Không tìm thấy user với username {username}")
    
    # Giả sử kết quả đầu tiên chính là user cần lấy
    return response.json()[0]["accountId"]

        
async def finalize_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Lấy thông tin từ context
        platform = context.user_data.get("platform", "").lower()
        user = users_collection.find_one({"chat_id": update.message.chat_id})
        
        if not user:
            await update.message.reply_text("❌ Vui lòng dùng /start trước!")
            return
        
        # Chuẩn bị dữ liệu task
        task_data = {
            "user_id": user["user_id"],
            "title": context.user_data.get("title", ""),
            "description": context.user_data.get("description", ""),
            "priority": context.user_data.get("priority", "medium").lower(),
            "assignees": context.user_data.get("assignees", []),
            "due_date": datetime.utcnow().isoformat(), 
            "status": "todo",
            "source_platform": platform
        }
        
     
        platform_id = await create_task_on_platform(platform, task_data)
        
        task_record = {
            **task_data,
            "id": f"{platform}:{platform_id}",
            "extend": {
                "labels": [],
                "project": os.getenv("JIRA_PROJECT_KEY") if platform == "jira" else None
            }
        }
        tasks_collection.insert_one(task_record)
        
        await update.message.reply_text(f"✅ Đã tạo task trên {platform}!")
    
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")

async def check_deadlines():
    now = datetime.now()
    three_days_later = now + timedelta(days=3)
    
    tasks = tasks_collection.find({
        "due_date": {"$lte": three_days_later.isoformat()},
        "status": {"$ne": "done"}
    })
    
    for task in tasks:
        assignees = task.get("assignees", [])
        
        for username in assignees:
            user = users_collection.find_one({"username": username})
            
            if user and user.get("active", True):
                await send_alert(user["chat_id"], task)

async def send_alert(chat_id: int, task: dict):
    status = task.get("status") or task.get("list_name")
    try:
        await Bot(token=TOKEN).send_message(
            chat_id=chat_id,
            text=f"⚠️ SẮP HẾT HẠN: {task['title']}\n"
                 f"📅 Deadline: {task['due_date']}\n"
                 f"📌 Trạng thái: {status.upper()}"
        )
    except Exception as e:
        print(f"Không gửi được cảnh báo đến {chat_id}: {str(e)}")

async def connect_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔗 Vui lòng nhập tên nền tảng bạn muốn kết nối (trello, jira, lark):"
    )
    return PLATFORM_SELECTED  # sử dụng state PLATFORM_SELECTED để xử lý input của người dùng
async def connect_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔗 Vui lòng nhập tên nền tảng bạn muốn kết nối (trello, jira, lark):"
    )
    return PLATFORM_SELECTED  # state để nhận input từ người dùng

async def handle_platform_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    platform = update.message.text.strip().lower()
    if platform not in ["trello", "jira", "lark"]:
        await update.message.reply_text(
            "❌ Nền tảng không hợp lệ, vui lòng nhập lại (trello, jira, lark):"
        )
        return PLATFORM_SELECTED
    if platform == "trello":
        return await handle_trello_connection(update, context)
    elif platform == "jira":
        return await handle_jira_connection(update, context)
    # elif platform == "lark":
    #     return await handle_lark_connection(update, context)
    else:
        await update.message.reply_text("❌ Nền tảng không hỗ trợ!")
        return ConversationHandler.END
def convert_text_to_adf(text: str) -> dict:
    """Chuyển đổi plain text sang Atlassian Document Format"""
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": text
                    }
                ]
            }
        ]
    }

# sửa lại nhập list name với board name với trello
async def handle_trello_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý kết nối Trello: Yêu cầu nhập tên Board và List"""
    await update.message.reply_text("📋 Nhập tên **Board** Trello của bạn:")
    return AWAITING_TRELLO_BOARD_NAME

async def get_trello_board_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lưu tên Board và yêu cầu nhập tên List"""
    context.user_data['trello_board'] = update.message.text
    await update.message.reply_text("📝 Nhập tên **List** trong Board:")
    return AWAITING_TRELLO_LIST_NAME

async def get_trello_list_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý tên List và lưu Board/List ID vào database"""
    try:
        board_name = context.user_data['trello_board']
        list_name = update.message.text

        # Lấy Board ID từ tên Board
        boards_url = "https://api.trello.com/1/members/me/boards"
        params = {
            'key': os.getenv("TRELLO_API_KEY"),
            'token': os.getenv("TRELLO_API_TOKEN")
        }
        response = requests.get(boards_url, params=params)
        board_id = next((b['id'] for b in response.json() if b['name'].lower() == board_name.lower()), None)

        if not board_id:
            raise Exception("Không tìm thấy Board!")

        # Lấy List ID từ tên List
        lists_url = f"https://api.trello.com/1/boards/{board_id}/lists"
        response = requests.get(lists_url, params=params)
        list_id = next((l['id'] for l in response.json() if l['name'].lower() == list_name.lower()), None)

        if not list_id:
            raise Exception("Không tìm thấy List!")

        # Lưu vào database
        user_credentials.update_one(
            {"user_id": update.effective_user.id, "platform": "trello"},
            {"$set": {
                "default_board": board_id,
                "default_list": list_id,
                "connected_at": datetime.now()
            }},
            upsert=True
        )

        await update.message.reply_text("✅ Kết nối Trello thành công!")
        return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return ConversationHandler.END
#jira
async def handle_jira_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý kết nối Jira: Yêu cầu nhập Project Key"""
    await update.message.reply_text("🔑 Nhập **Project Key** của Jira (ví dụ: VCC):")
    return AWAITING_JIRA_PROJECT_KEY

async def get_jira_project_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lưu Project Key vào database"""
    project_key = update.message.text.upper()
    user_credentials.update_one(
        {"user_id": update.effective_user.id, "platform": "jira"},
        {"$set": {"project_key": project_key}},
        upsert=True
    )
    await update.message.reply_text("✅ Kết nối Jira thành công!")
    return ConversationHandler.END
def start_scheduler():
    loop = asyncio.get_event_loop() 
    scheduler = AsyncIOScheduler(event_loop=loop)
    scheduler.add_job(check_deadlines, CronTrigger(hour=17, minute=18))  # Chạy hàng ngày lúc 9h
    scheduler.start()