from flask import Flask, jsonify, Blueprint
import requests
import os
from MongoDBConnection import MongoDBConnection
from service.response_body import Code, response_body, Status
from service.helpers import objectid_to_str
from dotenv import load_dotenv

trello_bp = Blueprint('trello', __name__, url_prefix='/trello')

load_dotenv()

TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_API_TOKEN = os.getenv("TRELLO_API_TOKEN")
TRELLO_BOARD_ID = os.getenv("TRELLO_BOARD_ID")

CARDS_URL = f"https://api.trello.com/1/boards/{TRELLO_BOARD_ID}/cards"
LISTS_URL = f"https://api.trello.com/1/boards/{TRELLO_BOARD_ID}/lists"


# Helper: Lấy danh sách các danh sách từ Trello
def fetch_trello_lists():
    params = {"key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN}
    response = requests.get(LISTS_URL, params=params)
    response.raise_for_status()
    lists = response.json()
    return {list_item["id"]: list_item["name"] for list_item in lists}


def fetch_board_details(board_id):
    board_url = f"https://api.trello.com/1/boards/{board_id}"
    params = {"key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN}
    response = requests.get(board_url, params=params)
    response.raise_for_status()
    return response.json()
def fetch_card_details(card_id):
    params = {
        "key": TRELLO_API_KEY,
        "token": TRELLO_API_TOKEN,
        "members": "true",           
        "member_fields": "email,fullName" , 
        "member_board": "true" 
    }
    detail_url = f"https://api.trello.com/1/cards/{card_id}"
    response = requests.get(detail_url, params=params)
    response.raise_for_status()
    return response.json()
# API: Lấy danh sách thẻ từ Trello và lưu vào MongoDB
@trello_bp.route('/cards')
def fetch_trello_cards():
    try:
        params = {"key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN }

        list_name_mapping = fetch_trello_lists()

        response = requests.get(CARDS_URL, params=params)
        response.raise_for_status()
        cards = response.json()

        result = []
        mongo_conn = MongoDBConnection()
        trello_tasks_collection11 = mongo_conn.get_collection("unified_tasks")

        for card in cards:
            details = fetch_card_details(card['id'])
            board_details = fetch_board_details(details.get("idBoard"))
            metadata = {
                "board": {
                    "id": details.get("idBoard"),
                    "name": board_details.get("name"),
                    "url": board_details.get("shortUrl") or board_details.get("url")
                },
                "list": {
                    "id": details.get("idList"),
                    "name": list_name_mapping.get(details.get("idList"), "Unknown List")
                },
                "labels": [label["name"] for label in details.get("labels", [])],
            }
            task_data = {
                "id": details.get("id"),
                "title": details.get("name"),
                "desc": details.get("description"),
                "list_name": list_name_mapping.get(details.get("idList"), "Unknown List"),
                "members": [
                    {
                        "name": member.get("fullName")
                    } 
               
                for member in details.get("members", [])
                ],
                "assignees": [member.get("fullName") for member in details.get("members", []) 
                if member.get("fullName")],
                "created_at": details.get("dateLastActivity"),
                "updated_at": details.get("dateLastActivity"),
                "due_date": details.get("due"),
                "source": "trello", 
                "extend": metadata,
            }

            task_data = objectid_to_str(task_data)
            trello_tasks_collection11.insert_one(task_data)
            result.append(task_data)
        
        response_body11 = response_body(
            code = Code.SUCCESS,
            result = None,
            status = Status.SUCCESS,
            message = "Tasks fetched and saved to MongoDB"
        )
        
        return jsonify(response_body11.__dict__)

    except requests.exceptions.RequestException as e:
        response_body2 = response_body(
            result = None,
            status = Status.FAILED,
            message = str(e)
        )
        return jsonify(response_body2.__dict__)

@trello_bp.route('/tasks/user/<user_id>')
def fetch_tasks_by_user(user_id):
    try:
        mongo_conn = MongoDBConnection()
        unified_tasks_collection = mongo_conn.get_collection("unified_tasks")
        query = {
            "$or": [
                {"members": user_id},
                {"assignees": user_id}
            ]
        }
        result = unified_tasks_collection.find(query)
        data = [objectid_to_str(doc) for doc in result]
        
        res_body  = response_body(
            code = Code.SUCCESS,
            result = data,
            status = Status.SUCCESS,
            message =f"Tasks for user {user_id} fetched successfully"
        )

        return jsonify(res_body.__dict__)

    except Exception as e:
        error_body  = response_body(
            result = None,
            status = Status.FAILED,
            message = str(e)
        )
        return jsonify(error_body .__dict__)


