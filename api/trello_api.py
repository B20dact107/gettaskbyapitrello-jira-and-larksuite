from flask import Flask, jsonify
import requests
from dotenv import load_dotenv
import os
from mongodb_connection import MongoDBConnection
from bson import ObjectId
from ResponseBody import ResponseBody, Status, Code 

load_dotenv()

app = Flask(__name__)

TRELLO_API_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_API_TOKEN = os.getenv("TRELLO_API_TOKEN")
TRELLO_BOARD_ID = os.getenv("TRELLO_BOARD_ID")

CARDS_URL = f"https://api.trello.com/1/boards/{TRELLO_BOARD_ID}/cards"
LISTS_URL = f"https://api.trello.com/1/boards/{TRELLO_BOARD_ID}/lists"

def objectid_to_str(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, list):
        return [objectid_to_str(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: objectid_to_str(value) for key, value in obj.items()}
    return obj

# Helper: Lấy danh sách các danh sách từ Trello
def fetch_trello_lists():
    params = {"key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN}
    response = requests.get(LISTS_URL, params=params)
    response.raise_for_status()
    lists = response.json()
    return {list_item["id"]: list_item["name"] for list_item in lists}

# Helper: Lấy chi tiết thẻ từ Trello
def fetch_card_details(card_id):
    params = {"key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN}
    detail_url = f"https://api.trello.com/1/cards/{card_id}"
    response = requests.get(detail_url, params=params)
    response.raise_for_status()
    return response.json()

# API: Lấy danh sách thẻ từ Trello và lưu vào MongoDB
@app.route('/trello/cards')
def fetch_trello_cards():
    try:
        params = {"key": TRELLO_API_KEY, "token": TRELLO_API_TOKEN}

        list_name_mapping = fetch_trello_lists()

        response = requests.get(CARDS_URL, params=params)
        response.raise_for_status()
        cards = response.json()

        result = []
        mongo_conn = MongoDBConnection()
        trello_tasks_collection = mongo_conn.get_collection("trello_tasks")

        for card in cards:
            details = fetch_card_details(card['id'])

            task_data = {
                "id": details.get("id"),
                "name": details.get("name"),
                "desc": details.get("desc"),
                "list_name": list_name_mapping.get(details.get("idList"), "Unknown List"),
                "members": [member["fullName"] for member in details.get("members", [])],
                "created_at": details.get("dateLastActivity"),
                "updated_at": details.get("dateLastActivity"),
                "due_date": details.get("due"),
                "labels": [label["name"] for label in details.get("labels", [])],
            }

            task_data = objectid_to_str(task_data)
            trello_tasks_collection.insert_one(task_data)
            result.append(task_data)
        
        response_body = ResponseBody(
            code= Code.SUCCESS,
            result=None,
            status=Status.SUCCESS,
            message="Tasks fetched and saved to MongoDB"
        )
        
        return jsonify(response_body.__dict__)

    except requests.exceptions.RequestException as e:
        response_body = ResponseBody(
            result=None,
            status=Status.FAILED,
            message=str(e)
        )
        return jsonify(response_body.__dict__)

@app.route('/trello/cards-db')
def fetch_trello_cards_from_db():
    try:
        mongo_conn = MongoDBConnection()
        trello_tasks_collection = mongo_conn.get_collection("trello_tasks")
        result = trello_tasks_collection.find()

        data = [objectid_to_str(doc) for doc in result]
        
        response_body = ResponseBody(
            code = Code.SUCCESS,
            result=data,
            status=Status.SUCCESS,
            message="Tasks fetched successfully from MongoDB"
        )

        return jsonify(response_body.__dict__)

    except Exception as e:
        response_body = ResponseBody(
            result=None,
            status=Status.FAILED,
            message=str(e)
        )
        return jsonify(response_body.__dict__)

if __name__ == '__main__':
    app.run(debug=True)
