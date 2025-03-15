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
user_credentials = db["user_credentials"]


# Thêm phần định nghĩa state ở đầu file
(AWAITING_TRELLO_CREDS, AWAITING_JIRA_CREDS,  AWAITING_LARK_CREDS, PLATFORM_SELECTED,AWAITING_TRELLO_BOARD_NAME,
    AWAITING_TRELLO_LIST_NAME,
    AWAITING_JIRA_PROJECT_KEY, AWAITING_LARK_TASKLIST_NAME) = range(5, 13)  

TOKEN = os.getenv("TELEGRAM_TOKEN")

async def check_trello_auth(user_id: int) -> bool:
    creds = user_credentials.find_one({
        "user_id": user_id,
        "platform": "trello"
    })
    return creds is not None and "default_board" in creds and "default_list" in creds

async def create_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = user_credentials.find_one({"chat_id": update.message.chat_id})
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

# (
#     PLATFORM_SELECTED,
#     AWAITING_TRELLO_BOARD_NAME,
#     AWAITING_TRELLO_LIST_NAME,
#     AWAITING_JIRA_PROJECT_KEY
# ) = range(4, 8)  


async def handle_platform_connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  
    platform = query.data.split("_")[1]
    
    if platform == "trello":
        return await handle_trello_connection(update, context)
    elif platform == "jira":
        return await handle_jira_connection(update, context)
    elif platform == "lark":
        return await handle_lark_connection(update, context)
    else:
        await query.answer("Nền tảng không hỗ trợ!")
        return ConversationHandler.END

async def start(update : Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    # Lưu thông tin người dùng vào collection 'users'
    db.user_credentials.update_one(
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
        "/username - Thiết lập username để có thể lấy ra danh sách task\n"  
        "/connect - Kết nối với Trello, Jira, Larksuite\n" 
        "/tasks - Hiển thị danh sách task (dùng user_id nếu cung cấp, "
        "nếu không thì dùng chat_id)\n"
        "/create_issue [nội dung] - Tạo task mới\n"
        "⚠️ Cảnh báo tự động sẽ được gửi khi task sắp hết hạn!"
    )
async def username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Vui lòng nhập username (ví dụ: /username sui00002002)")
        return
    
    new_username = context.args[0]
    user = update.message.from_user
    
    user_credentials.update_one(
        {"user_id": user.id},
        {"$set": {"username": new_username}},
        upsert=True
    )
    
    await update.message.reply_text(f"✅ Đã cập nhật username thành: {new_username}")
async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = user_credentials.find_one({"chat_id": update.message.chat_id})
    
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
            return card_id
            
        except Exception as e:
            raise Exception(f"Không thể tạo task trên Trello: {str(e)}")
        
    
    if platform == "jira":
        try:
            creds = user_credentials.find_one({
                "user_id": task_data["user_id"],
                "platform": "jira"
            })
            if not creds or not all([
                creds["jira_domain"],
                creds["jira_email"],
                creds["jira_api_token"],
                creds["project_key"]
            ]):
                raise Exception("Thiếu cấu hình Jira trong database!")
            
            url = f"https://{creds['jira_domain']}/rest/api/3/issue"

            adf_description = convert_text_to_adf(task_data.get("description", ""))
            username_input = task_data.get("assignees", [""])[0]
            if not username_input:
                account_id = None
            else:
                account_id = get_jira_account_id_from_username(username_input)
        
            
            # Chuẩn bị payload
            payload = {
                "fields": {
                    "project": {"key": creds["project_key"]},
                    "issuetype": {"name": "Task"},  
                    "summary": task_data["title"],
                    "description": adf_description,
                    "assignee": {"accountId": account_id} if account_id else None
                    
                }
            }
           
            # Gọi API Jira
            response = requests.post(
                url,
                auth=HTTPBasicAuth(creds["jira_email"], creds["jira_api_token"]),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                json=payload,
                timeout=10
            )
            
            
            if response.status_code == 201:
                return response.json().get("id")
            else:
                raise Exception(f"Jira API Error ({response.status_code}): {response.text}")
        
        except Exception as e:
            raise Exception(f"Không thể tạo task trên Jira: {str(e)}")
        
    
    
    elif platform == "lark":
        try:
            # Lấy access token từ DB bằng cách truyền user_id từ task_data
            access_token = get_lark_access_token(task_data["user_id"])
        # Gọi API tạo task
            creds = user_credentials.find_one({
                "user_id": task_data["user_id"], 
                "platform": "lark"
            })
            
            if not creds or "default_tasklist" not in creds:
                raise Exception("Chưa chọn task list trên Lark!")
            
            url = "https://open.larksuite.com/open-apis/task/v2/tasks"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            members = []
            for username in task_data.get("assignees", []):
                user = user_credentials.find_one({"username": username})
                if user:
                    members.append({"id": str(user["user_id"])})
            tasklist_guid = creds["default_tasklist"]
            payload = {
                "summary": task_data["title"].strip(),
                "description": task_data.get("description", ""),
                "due": {
                    "timestamp": int((datetime.fromisoformat(task_data["due_date"])).timestamp() * 1000),
                    "is_all_day": False  # Điều chỉnh nếu cần
                },
                "tasklists": [
                    {"tasklist_guid": tasklist_guid}
                ]
            }

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code != 200:
                raise Exception(f"Lỗi Lark API: {response.text}")

            return response.json()["data"]["task"]["guid"]
            
        except Exception as e:
            raise Exception(f"Lỗi tạo task trên Lark: {str(e)}")

def get_jira_account_id_from_username(username: str) -> str:
    url = f"https://{os.getenv('JIRA_DOMAIN')}/rest/api/3/user/search"
    auth = HTTPBasicAuth(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))
    params = {"query": username}
    response = requests.get(url, params=params, auth=auth, headers={"Accept": "application/json"})

    if response.status_code != 200 or not response.json():
        raise Exception(f"Không tìm thấy user với username {username}")
    
    # Giả sử kết quả đầu tiên chính là user cần lấy
    account_id =response.json()[0]["accountId"]
    return response.json()[0]["accountId"]

        
async def finalize_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Lấy thông tin từ context
        platform = context.user_data.get("platform", "").lower()
        user = user_credentials.find_one({"chat_id": update.message.chat_id})
        if not user:
            await update.message.reply_text("❌ Vui lòng dùng /start trước!")
            return
        current_username = update.message.from_user.username
        if user.get("username") != current_username:
            user_credentials.update_one(
                {"user_id": user["user_id"]},
                {"$set": {"username": current_username}}
            )
        
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
            user = user_credentials.find_one({"username": username})
            
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
    elif platform == "lark":
        return await handle_lark_connection(update, context)
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
                "api_key": os.getenv("TRELLO_API_KEY"),
                "token": os.getenv("TRELLO_API_TOKEN"),
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
        {"$set": {
            "project_key": project_key,
            "jira_email" :os.getenv("JIRA_EMAIL"),
            "jira_domain":os.getenv("JIRA_DOMAIN"),
            "jira_api_token": os.getenv("JIRA_API_TOKEN")
            }},
        upsert=True
    )
    await update.message.reply_text("✅ Kết nối Jira thành công!")
    return ConversationHandler.END
#larksuite
async def handle_lark_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tự động kết nối LarkSuite bằng thông tin từ .env"""
    user_id = update.effective_user.id
    
    app_id = os.getenv("LARKSUITE_APP_ID")
    app_secret = os.getenv("LARKSUITE_APP_SECRET")
    larkurl = os.getenv("LARKSUITE_OAUTH_AUTHORIZE_URL")
    lark_redirect_uri = 'http://127.0.0.1:5000/oauth/callback'
    
    oauth_url = (
         f"https://open.larksuite.com/open-apis/authen/v1/index?"
         f"app_id={app_id}&"
         f"redirect_uri={lark_redirect_uri}"
    )
    await update.message.reply_text(
        "🔑 Vui lòng truy cập URL sau để cấp quyền cho ứng dụng:\n"
        f"{oauth_url}\n\n"
        "Sau khi đồng ý, hãy nhập CODE bạn nhận được từ trang xác thực."
    )
    return AWAITING_LARK_CREDS

async def handle_lark_authorization_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    user_id = update.effective_user.id
    
    try:
        # Gọi API để lấy access token
        token_url = "https://open.larksuite.com/open-apis/authen/v1/access_token"
        headers = {"Content-Type": "application/json"}
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "app_id": os.getenv("LARKSUITE_APP_ID"),
            "app_secret": os.getenv("LARKSUITE_APP_SECRET")
        }
        
        response = requests.post(token_url, json=payload, headers=headers)
        response_data = response.json()
        
        if response_data.get("code") != 0:
            raise Exception(f"Lỗi Lark API: {response_data.get('msg')}")
            
        # Lưu thông tin token vào database
        user_credentials.update_one(
            {"user_id": user_id, "platform": "lark"},
            {"$set": {
                "access_token": response_data["data"]["access_token"],
                "refresh_token": response_data["data"]["refresh_token"],
                "expires_in": response_data["data"]["expires_in"],
                "connected_at": datetime.now()
            }},
            upsert=True
        )
        
        await update.message.reply_text("📋 Nhập TÊN TASK LIST chính xác trên Lark:")
        return AWAITING_LARK_TASKLIST_NAME  
        
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return ConversationHandler.END
async def handle_lark_tasklist_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tasklist_name = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Lấy access token từ DB
        access_token = get_lark_access_token(user_id)
        
        # Gọi API tìm kiếm task list
        url = "https://open.larksuite.com/open-apis/task/v2/tasklists"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        tasklist = next(
            (tl for tl in response.json()["data"]["items"] if tl["name"].lower() == tasklist_name.lower()),
            None
        )
        
        if not tasklist:
            raise Exception(f"Không tìm thấy task list với tên '{tasklist_name}'")
        
        user_credentials.update_one(
            {"user_id": user_id, "platform": "lark"},
            {"$set": {"default_tasklist": tasklist["guid"]}}
        )
        
        await update.message.reply_text(f"✅ Đã chọn task list '{tasklist_name}' thành công!")
        return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {str(e)}")
        return ConversationHandler.END
def get_lark_access_token(user_id: int):
    """Lấy access token từ database và tự động renew nếu hết hạn"""
    creds = user_credentials.find_one({"user_id": user_id, "platform": "lark"})
    
    if not creds:
        raise Exception("Chưa kết nối LarkSuite. Dùng lệnh /connect lark để kết nối")
    
    # Kiểm tra thời hạn token
    expires_at = creds["connected_at"] + timedelta(seconds=creds["expires_in"] - 300)  # Trừ 5p để đề phòng
    if datetime.now() < expires_at:
        return creds["access_token"]
    
    # Tự động renew token nếu hết hạn
    print("🔄 Token hết hạn, đang renew...")
    refresh_url = "https://open.larksuite.com/open-apis/authen/v1/refresh_access_token"
    headers = {"Content-Type": "application/json"}
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": creds["refresh_token"],
        "app_id": os.getenv("LARKSUITE_APP_ID"),
        "app_secret": os.getenv("LARKSUITE_APP_SECRET")
    }
    
    response = requests.post(refresh_url, json=payload, headers=headers)
    refresh_data = response.json()
    
    if refresh_data.get("code") != 0:
        raise Exception(f"Lỗi renew token: {refresh_data.get('msg')}")
    
    # Cập nhật database
    user_credentials.update_one(
        {"_id": creds["_id"]},
        {"$set": {
            "access_token": refresh_data["data"]["access_token"],
            "refresh_token": refresh_data["data"]["refresh_token"],
            "expires_in": refresh_data["data"]["expires_in"],
            "connected_at": datetime.now()
        }}
    )
    
    return refresh_data["data"]["access_token"]
    
def start_scheduler(loop):
    #loop = asyncio.get_event_loop() 
    scheduler = AsyncIOScheduler(event_loop=loop)
    scheduler.add_job(check_deadlines, CronTrigger(hour=9, minute=0))  # Chạy hàng ngày lúc 9h
    scheduler.start()