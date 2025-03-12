from bson import ObjectId
import requests
from functools import wraps
from flask import jsonify
from api.response_body import Code, response_body, Status

def objectid_to_str(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, list):
        return [objectid_to_str(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: objectid_to_str(value) for key, value in obj.items()}
    return obj
def objectid_to_str_lark(task):
    for key, value in task.items():
        if isinstance(value, ObjectId):
            task[key] = str(value) 
    return task
def get_user_name(user_id: str, access_token: str) -> str:
    
    url = f"https://open.larksuite.com/open-apis/contact/v3/users/{user_id}?user_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 0:
            # Lấy en_name từ data -> user -> en_name
            return data.get("data", {}).get("user", {}).get("en_name")
        else:
            print("Error from LarkSuite API:", data.get("msg"))
            return None
    except Exception as e:
        print("HTTP error:", str(e))
        return None
def handle_api_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return jsonify(response_body(
                result=None,
                status=Status.FAILED,
                message=str(e),
                code=Code.CLIENT_ERROR
            ).to_dict()), 400
        except PermissionError as e:
            return jsonify(response_body(
                result=None,
                status=Status.FAILED,
                message=str(e),
                code=Code.UNAUTHORIZED_REQUEST
            ).to_dict()), 403
        except Exception as e:
            return jsonify(response_body(
                result=None,
                status=Status.FAILED,
                message=str(e),
                code=Code.INTERNAL_ERROR
            ).to_dict()), 500
    return wrapper