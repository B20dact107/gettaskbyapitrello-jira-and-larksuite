from datetime import datetime
from dateutil import parser as date_parser

from typing import List, Optional, Dict, Any
from enum import Enum

from flask import json
import re

from models.JiraTask import JiraTask
from models.LarksuiteTask import LarksuiteTask
from models.TrelloTask import TrelloTask

class TaskStatus(str, Enum):
    TODO = "to_do"
    Doing = "doing"
    DONE = "done"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Task:
    def __init__(
        self,
        task_id: str,
        title: str,
        source: str,  # "jira", "trello", "larksuite"
        status: TaskStatus,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        due_date: Optional[datetime] = None,
        description: Optional[str] = None,
        assignees: List[str] = [],
        priority: TaskPriority = TaskPriority.MEDIUM,
        extend: Dict[str, Any] = {}  # Chứa dữ liệu đặc thù platform
    ):
        self.id = f"{source}:{task_id}"
        self.title = title
        self.source = source
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.due_date = due_date
        self.description = description
        self.assignees = assignees
        self.priority = priority
        self.extend = extend

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "description": self.description,
            "assignees": self.assignees,
            "priority": self.priority.value,
            "extend": self.extend
        }

    @classmethod
    def from_jira(cls, jira_task: 'JiraTask'):
        # project_info = {
        # "_id": getattr(jira_task, "project_id", None),             # Ví dụ: jira_task.project_id
        # "name": getattr(jira_task, "project_name", None),            # Ví dụ: jira_task.project_name
        # "description": getattr(jira_task, "project_description", None),  # Ví dụ: jira_task.project_description
        # "owner": getattr(jira_task, "project_owner", None),          # Ví dụ: jira_task.project_owner
        # "members": getattr(jira_task, "project_members", [])         # Ví dụ: jira_task.project_members
        # }
        jira_status_map = {
            "done": TaskStatus.DONE,
            "in_progress": TaskStatus.Doing,
        }
        original_status = jira_task.status.lower().replace(" ", "_")
        normalized_status = jira_status_map.get(original_status, TaskStatus.TODO)
     
        return cls(
            task_id=jira_task.id,
            title=jira_task.summary,
            source="jira",
            status=normalized_status,
            created_at = date_parser.parse(jira_task.created),
            updated_at = date_parser.parse(jira_task.updated) if jira_task.updated else None,
            due_date = date_parser.parse(jira_task.due_date) if jira_task.due_date else None,
            description=jira_task.description,
            assignees=jira_task.assignees,
            priority=TaskPriority(jira_task.priority.lower() if jira_task.priority else "medium"),
            extend={
                "labels": jira_task.labels,
                "project": {
                    "key": getattr(jira_task, "project_key", None),
                    "name": getattr(jira_task, "project_name", None)
                },
                "issue_type": getattr(jira_task, "issue_type", None),
                "components": getattr(jira_task, "components", None),
                "versions": getattr(jira_task, "versions", None),
                "resolution": getattr(jira_task, "resolution_status", None)
            }
           
        )
    
    @classmethod
    def from_larksuite(cls, larksuite_task: 'LarksuiteTask'):
        status = TaskStatus.DONE if larksuite_task.completed_at != "0" else TaskStatus.Doing
    
    # Xử lý thời gian
        start_date = None
        if larksuite_task.start and "timestamp" in larksuite_task.start:
            start_date = datetime.fromtimestamp(int(larksuite_task.start["timestamp"]) / 1000)

        due_date = None
        if larksuite_task.due and "timestamp" in larksuite_task.due:
            due_date = datetime.fromtimestamp(int(larksuite_task.due["timestamp"])/1000)
        print(f"mo tả ",larksuite_task.description)
        original_summary = (larksuite_task.summary or "").strip()
        priority_map = {
            "h": TaskPriority.HIGH,
            "m": TaskPriority.MEDIUM,
            "l": TaskPriority.LOW
        }
        extracted_priority = None
        # Tìm mẫu ký hiệu ở cuối summary, ví dụ "(h)", "(m)" hoặc "(l)"
        match = re.search(r'\(([hmlHML])\)\s*$', original_summary)
        if match:
            code = match.group(1).lower()
            extracted_priority = priority_map.get(code, TaskPriority.MEDIUM)
        # Loại bỏ phần "(h)" ra khỏi summary
            new_summary = re.sub(r'\(([hmlHML])\)\s*$', '', original_summary)
        else:
            new_summary = original_summary
            extracted_priority = TaskPriority.MEDIUM 
        
        return cls(
            task_id=larksuite_task.task_id,
            title=new_summary,
            source="larksuite",
            status=status,
            due_date=due_date,
            created_at=start_date,
            priority=extracted_priority,
            assignees=larksuite_task.members,
            description=larksuite_task.description,
            extend={
                "subtask_count": larksuite_task.subtask_count,
                "platform_data": larksuite_task.extra_data
            }
        )
       
    @classmethod
    def from_trello(cls, trello_task: 'TrelloTask'):
        status_mapping = {
            "To Do": TaskStatus.TODO,
            "Doing": TaskStatus.Doing,
            "Done": TaskStatus.DONE
        }
        status = status_mapping.get(trello_task.list_name, TaskStatus.TODO)
        
        created_at = date_parser.parse(trello_task.created_at) if trello_task.created_at else None
        updated_at = date_parser.parse(trello_task.updated_at) if trello_task.updated_at else None
        due_date = date_parser.parse(trello_task.due_date) if trello_task.due_date else None
        
        return cls(
            task_id=trello_task.id,
            title=trello_task.title,
            source="trello",
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            due_date=due_date,
            description=trello_task.desc,
            assignees=trello_task.members,
            priority=TaskPriority.MEDIUM,
            extend={
                "board": {
                    "id": trello_task.board_id,
                    "name": trello_task.board_name,
                    "url": trello_task.board_url
                },
                "list": {
                    "id": trello_task.list_id,
                    "name": trello_task.list_name
                },
                "checklists": {
                    "total": trello_task.checklist_count,
                    "completed": trello_task.checklist_completed
                },
                "labels": trello_task.labels
            }
            
        )