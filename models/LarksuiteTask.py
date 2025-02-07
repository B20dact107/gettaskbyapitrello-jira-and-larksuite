# from typing import List, Optional
# from datetime import datetime

# # Class đại diện cho task từ Larksuite
# class LarksuiteTask:
#     def __init__(
#         self,
#         task_id: str,
#         summary: str,
#         completed_at: Optional[str] = "0",
#         due: Optional[dict] = None,
#         start: Optional[dict] = None,
#         members: List[dict] = [],
#         subtask_count: int = 0,
#         page_token: Optional[str] = None,
#     ):
#         self.task_id = task_id
#         self.summary = summary
#         self.completed_at = completed_at
#         self.due = due
#         self.start = start
#         self.members = members
#         self.subtask_count = subtask_count
#         self.page_token = page_token

#     @staticmethod
#     def _parse_timestamp(timestamp: Optional[str]) -> Optional[str]:
#         """Chuyển đổi timestamp thành định dạng ISO 8601."""
#         if timestamp and timestamp != "0":
#             try:
#                 return datetime.fromtimestamp(int(timestamp) / 1000).isoformat()
#             except ValueError:
#                 pass
#         return None

#     def to_dict(self):
#         """Chuyển đối tượng thành dictionary để tuần tự hóa."""
#         members_dict = [{"id": m["id"], "role": m["role"], "type": m["type"]} for m in self.members]
#         return {
#             "completed_at": self.completed_at,
#             "guid": self.task_id,
#             "members": members_dict,
#             "subtask_count": self.subtask_count,
#             "summary": self.summary,
#             "due": self.due,
#             "start": self.start,
#             "page_token": self.page_token,
#         }

#     def __repr__(self):
#         return f"<LarksuiteTask task_id={self.task_id} summary={self.summary}>"

# # Hàm để chuyển đổi JSON thành danh sách đối tượng LarksuiteTask
# def parse_tasks_from_json(json_data: dict) -> List[LarksuiteTask]:
#     tasks = []
#     for item in json_data.get("data", {}).get("items", []):
#         task_id = item.get("guid", "")
#         summary = item.get("summary", "")
#         completed_at = item.get("completed_at", "0")
#         subtask_count = item.get("subtask_count", 0)
#         page_token = item.get("page_token", None)

#         # Xử lý deadline (due) và thời gian bắt đầu (start)
#         due = item.get("due", {})
#         start = item.get("start", {})

#         members = item.get("members", [])
        
#         task = LarksuiteTask(
#             task_id=task_id,
#             summary=summary,
#             completed_at=completed_at,
#             due=due,
#             start=start,
#             members=members,
#             subtask_count=subtask_count,
#             page_token=page_token
#         )
#         tasks.append(task)
#     return tasks
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class LarksuiteTask:
    task_id: str
    summary: str
    completed_at: str
    due: Dict[str, Any]
    members: list
    subtask_count: int
    extra_data: Dict[str, Any]

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "summary": self.summary,
            "completed_at": self.completed_at,
            "due": self.due,
            "members": self.members,
            "subtask_count": self.subtask_count,
            "extra_data": self.extra_data
        }