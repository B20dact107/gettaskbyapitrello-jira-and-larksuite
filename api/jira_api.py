from dotenv import load_dotenv
from flask import Flask, jsonify, request
import requests
from requests.auth import HTTPBasicAuth
import os 
from models.JiraTask import JiraTask
from api.response_body import Code, response_body, Status

from MongoDBConnection import MongoDBConnection
from bson import ObjectId

from models.Task import Task

def objectid_to_str(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, list):
        return [objectid_to_str(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: objectid_to_str(value) for key, value in obj.items()}
    return obj

load_dotenv()

app = Flask(__name__)

JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
@app.route('/jira/task')
def get_jira_tasks():
    try:
        jql = request.args.get("jql")
        if not jql:
            return jsonify(response_body(None, Status.FAILED, "Parameter 'jql' is required", Code.INVALID_REQUEST_FORMAT).to_dict()), 400
            #return jsonify({"error": "Parameter 'jql' is required"}), 400

        url = f"https://{JIRA_DOMAIN}/rest/api/3/search"
        query = {"jql": jql, "maxResults": 10}

        response = requests.get(
            url,
            params = query,
            auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),
            headers = {"Accept": "application/json"}
        )


        if response.status_code == 200:
            issues = response.json().get("issues", [])
            tasks = []
            mongo_conn = MongoDBConnection()
            jira_tasks_collection = mongo_conn.get_collection("jira_tasks")
            common_tasks_collection = mongo_conn.get_collection("unified_tasks")


            for issue in issues:
                task_id = issue.get("id")
                task_summary = issue.get("fields", {}).get("summary")
                task_description = issue.get("fields", {}).get("description")
                task_status = issue.get("fields", {}).get("status", {}).get("name")
                task_priority = issue.get("fields", {}).get("priority", {}).get("name")
                task_created = issue.get("fields", {}).get("created")
                task_updated = issue.get("fields", {}).get("updated")
                task_due_date = issue.get("fields", {}).get("duedate")
                task_labels = issue.get("fields", {}).get("labels", [])
                assignees = []

                # Lấy thông tin assignee
                assignee_field = issue.get("fields", {}).get("assignee")
                if assignee_field:
                    assignees.append(assignee_field.get("displayName"))

                jira_task = JiraTask(
                    id = task_id,
                    summary = task_summary,
                    description = task_description,
                    status = task_status,
                    priority = task_priority,
                    assignees = assignees,
                    created = task_created,
                    updated = task_updated,
                    due_date = task_due_date,
                    labels = task_labels,
                )
                tasks.append(jira_task)
                common_task = Task.from_jira(jira_task)  # Chuyển đổi sang Task chung
                tasks.append(common_task)
                jira_tasks_collection.insert_one(jira_task.to_dict())
                common_tasks_collection.insert_one(common_task.to_dict())

            return jsonify(response_body([jira_task.to_dict() for jira_task in tasks], Status.SUCCESS).to_dict())

        else:
            return jsonify(response_body(None, Status.FAILED, response.text, Code.CLIENT_ERROR).to_dict()), response.status_code

    except Exception as e:
        return jsonify(response_body(None, Status.FAILED, str(e), Code.INTERNAL_ERROR).to_dict())

    #             tasks.append(task)
    #             jira_tasks_collection.insert_one(task.to_dict())
    #             tasks.append(task)

    #         # Chuyển đổi danh sách các đối tượng JiraTask thành JSON
    #         return jsonify([task.to_dict() for task in tasks])

    #     else:
    #         return jsonify({"error": response.text}), response.status_code

    # except Exception as e:
    #     return jsonify({"error": str(e)})
@app.route('/jira/tasksdb')
def get_jira_tasks_from_db():
    try:
        mongo_conn = MongoDBConnection()  
        jira_tasks_collection = mongo_conn.get_collection("jira_tasks")
        
        tasks_cursor = jira_tasks_collection.find()  
        
        tasks = []  

   
        for task in tasks_cursor:
            task = objectid_to_str(task)  
            tasks.append(task)

        response_body = response_body(
            code = Code.SUCCESS,
            result = tasks,
            status = Status.SUCCESS,
            message = "Tasks fetched successfully from MongoDB"
        )

        return jsonify(response_body.to_dict())

    except Exception as e:
        response_body = response_body(
            result = None,
            status = Status.FAILED,
            message = str(e)
        )
        return jsonify(response_body.to_dict())


if __name__ == '__main__':
    app.run(debug = True)