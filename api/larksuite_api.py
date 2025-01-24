from flask import Flask, jsonify, request, redirect
import requests

from ResponseBody import Code, ResponseBody, Status
from models.LarksuiteTask import parse_tasks_from_json
from mongodb_connection import MongoDBConnection
from dotenv import load_dotenv
import os
from bson import ObjectId

load_dotenv()

app = Flask(__name__)

# Lấy API key và token từ biến môi trường
LARKSUITE_APP_ID = os.getenv("LARKSUITE_APP_ID")
LARKSUITE_APP_SECRET = os.getenv("LARKSUITE_APP_SECRET")
LARKSUITE_OAUTH_AUTHORIZE_URL = os.getenv("LARKSUITE_OAUTH_AUTHORIZE_URL")
LARKSUITE_OAUTH_TOKEN_URL = os.getenv("LARKSUITE_OAUTH_TOKEN_URL")
LARKSUITE_TASKLIST_URL = os.getenv("LARKSUITE_TASKLIST_URL")
def objectid_to_str(task):
    for key, value in task.items():
        if isinstance(value, ObjectId):
            task[key] = str(value) 
    return task

# Step 1: Bắt đầu OAuth flow
@app.route('/oauth/authorize')
def authorize():
    return redirect(
        f"{LARKSUITE_OAUTH_AUTHORIZE_URL}?app_id={LARKSUITE_APP_ID}&redirect_uri=http://127.0.0.1:5000/oauth/callback&response_type=code&state=custom_state"
    )

# Step 2: Đổi Authorization Code thành User Access Token
@app.route('/oauth/callback')
def oauth_callback():
    """Đổi Authorization Code thành User Access Token."""
    code = request.args.get('code')
    if not code:
        response = ResponseBody(
            result=None,
            status=Status.FAILED,
            message="Authorization code is missing",
            code=Code.CLIENT_ERROR
        )
        return jsonify(response.to_dict())

    try:
        response = requests.post(
            LARKSUITE_OAUTH_TOKEN_URL,
            headers={"Content-Type": "application/json"},
            json={"app_id": LARKSUITE_APP_ID, "app_secret": LARKSUITE_APP_SECRET, "grant_type": "authorization_code", "code": code},
        )
        response.raise_for_status()
        return jsonify(response.json())
    except requests.RequestException as e:
        response = ResponseBody(
            result=None,
            status=Status.FAILED,
            message=str(e),
            code=Code.INTERNAL_ERROR
        )
        return jsonify(response.to_dict())
    
# Step 3: Liệt kê tất cả tasklists
@app.route('/list-tasklists')
def list_tasklists():
    """Liệt kê tất cả các tasklists mà người dùng có quyền đọc."""
    access_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not access_token:
        response = ResponseBody(
            result=None,
            status=Status.FAILED,
            message="User access token is required",
            code=Code.UNAUTHORIZED_REQUEST
        )
        return jsonify(response.to_dict())

    page_size = request.args.get('page_size', 50)
    params = {"page_size": page_size}

    try:
        response = requests.get(
            LARKSUITE_TASKLIST_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            },
            params=params
        )
        response.raise_for_status()
        return jsonify(response.json())
    except requests.RequestException as e:
        response = ResponseBody(
            result=None,
            status=Status.FAILED,
            message=str(e),
            code=Code.INTERNAL_ERROR
        )
        return jsonify(response.to_dict())

# Step 4: Lấy danh sách tasks từ tasklist
@app.route('/get-tasks')
def get_tasks():
    """Lấy danh sách tasks từ một tasklist, lưu vào MongoDB và trả về danh sách tasks theo ResponseBody."""
    try:
        tasklist_guid = request.args.get('tasklist_guid')
        if not tasklist_guid:
            response = ResponseBody(
                result=None,
                status=Status.FAILED,
                message="tasklist_guid is required",
                code=Code.CLIENT_ERROR
            )
            return jsonify(response.to_dict())

        params = {
            "page_size": request.args.get('page_size', 50),
            "page_token": request.args.get('page_token', ''),
            "completed": request.args.get('completed'),
            "created_from": request.args.get('created_from'),
            "created_to": request.args.get('created_to'),
            "user_id_type": request.args.get('user_id_type', 'open_id'),
        }
        params = {k: v for k, v in params.items() if v is not None}

        # Lấy `access_token` từ header
        access_token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not access_token:
            response = ResponseBody(
                result=None,
                status=Status.FAILED,
                message="User access token is required",
                code=Code.UNAUTHORIZED_REQUEST
            )
            return jsonify(response.to_dict())

        response = requests.get(
            f"{LARKSUITE_TASKLIST_URL}/{tasklist_guid}/tasks",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            },
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        mongo_connection = MongoDBConnection()
        task_collection = mongo_connection.get_collection("larksuite_tasks")
        # Lưu các task vào MongoDB
        tasks = []
        if "data" in data and "items" in data["data"]:
            tasks = data["data"]["items"]
            for task in tasks:
                task["tasklist_guid"] = tasklist_guid
            task_collection.insert_many(tasks)

        response = ResponseBody(
            result=None,
            status=Status.SUCCESS,
            code=Code.SUCCESS
        )
        return jsonify(response.to_dict())

    except requests.RequestException as e:
        response = ResponseBody(
            result=None,
            status=Status.FAILED,
            message=str(e),
            code=Code.INTERNAL_ERROR
        )
        return jsonify(response.to_dict())
    
@app.route('/get-tasksdb')
def get_tasks_from_db():
    """Lấy danh sách tasks đã lưu trong MongoDB."""
    try:
        mongo_connection = MongoDBConnection()
        task_collection = mongo_connection.get_collection("larksuite_tasks")
        tasks = list(task_collection.find())  # Lấy tất cả tasks từ MongoDB
        tasks = [objectid_to_str(task) for task in tasks]
        
        response = ResponseBody(
            result=tasks,
            status=Status.SUCCESS,
            code=Code.SUCCESS
        )
        return jsonify(response.to_dict())

    except Exception as e:
        response = ResponseBody(
            result=None,
            status=Status.FAILED,
            message=str(e),
            code=Code.INTERNAL_ERROR
        )
        return jsonify(response.to_dict())

if __name__ == '__main__':
    app.run(debug=True)
