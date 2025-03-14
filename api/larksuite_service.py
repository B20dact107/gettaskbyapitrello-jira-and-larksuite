# services/larksuite_service.py
from flask import Blueprint, request, jsonify, redirect
import requests
import os
from api.response_body import Code, response_body, Status
from models.LarksuiteTask import LarksuiteTask
from models.Task import Task
from MongoDBConnection import MongoDBConnection
from api.helpers import handle_api_errors, objectid_to_str, get_user_name
from dotenv import load_dotenv
lark_bp = Blueprint('lark', __name__, url_prefix='/')
load_dotenv()
# Config
LARK_CONFIG = {
    "app_id": os.getenv("LARKSUITE_APP_ID"),
    "app_secret": os.getenv("LARKSUITE_APP_SECRET"),
    "authorize_url": os.getenv("LARKSUITE_OAUTH_AUTHORIZE_URL"),
    "token_url": os.getenv("LARKSUITE_OAUTH_TOKEN_URL"),
    "tasklist_url": os.getenv("LARKSUITE_TASKLIST_URL"),
    "redirect_uri": "http://127.0.0.1:5000/oauth/callback"
}

class LarkAuthService:
    @staticmethod
    def get_auth_url():
        return f"{LARK_CONFIG['authorize_url']}?app_id={LARK_CONFIG['app_id']}" \
               f"&redirect_uri={LARK_CONFIG['redirect_uri']}" \
               "&response_type=code&state=lark_auth"

    @staticmethod
    def exchange_code(code: str):
        try:
            response = requests.post(
                LARK_CONFIG['token_url'],
                json={
                    "app_id": LARK_CONFIG['app_id'],
                    "app_secret": LARK_CONFIG['app_secret'],
                    "grant_type": "authorization_code",
                    "code": code
                },
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Token exchange failed: {str(e)}")

class LarkTaskService:
    def __init__(self):
        self.mongo = MongoDBConnection()

    def fetch_tasks(self, tasklist_guid: str, access_token: str, params: dict):
        try:
            response = requests.get(
                f"{LARK_CONFIG['tasklist_url']}/{tasklist_guid}/tasks",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                params=params
            )
            response.raise_for_status()
            return self._process_tasks(response.json(), access_token)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch tasks: {str(e)}")

    def _process_tasks(self, data: dict, access_token: str):
        tasks = []
        if "data" in data and "items" in data["data"]:
            for raw_task in data["data"]["items"]:
                # Process members
                members = [
                    get_user_name(member.get("id"), access_token)
                    for member in raw_task.get("members", [])
                    if member.get("id")
                ]

                # Create domain object
                lark_task = LarksuiteTask(
                    task_id=raw_task.get("guid"),
                    summary=raw_task.get("summary"),
                    completed_at=raw_task.get("completed_at"),
                    due=raw_task.get("due"),
                    members=members,
                    subtask_count=raw_task.get("subtask_count", 0),
                    priority=raw_task.get("priority"),
                    start=raw_task.get("start"),
                    status=raw_task.get("status"),
                    description=raw_task.get("description"),
                    extra_data=raw_task
                )

                # Save to databases
                self._save_to_mongo(lark_task)
                tasks.append(lark_task)
        return tasks

    def _save_to_mongo(self, task: LarksuiteTask):
        self.mongo.get_collection("larksuite_tasks").insert_one(task.to_dict())
        unified_task = Task.from_larksuite(task)
        self.mongo.get_collection("unified_tasks").insert_one(unified_task.to_dict())

# Initialize services
auth_service = LarkAuthService()
task_service = LarkTaskService()

### 2. Cải thiện routes với error handling ###
@lark_bp.route('/oauth/authorize')
def authorize():
    """Redirect to LarkSuite authorization page"""
    return redirect(auth_service.get_auth_url())

@lark_bp.route('/oauth/callback')
# def oauth_callback():
    # """Exchange authorization code for access token"""
    # code = request.args.get('code')
    # if not code:
    #     return jsonify(response_body(
    #         status=Status.FAILED,
    #         message="Missing authorization code",
    #         code=Code.CLIENT_ERROR
    #     ).to_dict()), 400

    # try:
    #     token_data = auth_service.exchange_code(code)
    #     return jsonify(response_body(
    #         result=token_data,
    #         status=Status.SUCCESS
    #     ).to_dict())
    # except Exception as e:
    #     return jsonify(response_body(
    #         status=Status.FAILED,
    #         message=str(e),
    #         code=Code.INTERNAL_ERROR
    #     ).to_dict()), 500

@lark_bp.route('/tasks')
@handle_api_errors
def get_tasks():
    """Fetch tasks from specified tasklist"""
    # Validate inputs
    tasklist_guid = request.args.get('tasklist_guid')
    access_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if not tasklist_guid:
        raise ValueError("tasklist_guid is required")
    if not access_token:
        raise PermissionError("Access token is required")

    # Build query params
    params = {
        "page_size": request.args.get('page_size', 50),
        "completed": request.args.get('completed'),
        "created_from": request.args.get('created_from'),
        "created_to": request.args.get('created_to')
    }
    params = {k: v for k, v in params.items() if v is not None}

    # Fetch and process tasks
    tasks = task_service.fetch_tasks(tasklist_guid, access_token, params)
    return jsonify(response_body(
        result=[task.to_dict() for task in tasks],
        status=Status.SUCCESS
    ).to_dict())

@lark_bp.route('/tasks/db')
@handle_api_errors
def get_db_tasks():
    """Retrieve stored tasks from MongoDB"""
    tasks = list(task_service.mongo.get_collection("larksuite_tasks").find())
    return jsonify(response_body(
        result=[objectid_to_str(task) for task in tasks],
        status=Status.SUCCESS
    ).to_dict())