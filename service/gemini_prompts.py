TASK_CREATION_PROMPT = """
Bạn là hệ thống xử lý task tự động. Hãy phân tích câu lệnh và trả về JSON với các trường:
- title (bắt buộc)
- platform (mặc định: trello)
- description (tối đa 200 từ)
- assignees (mảng tên người dùng)
- due_date (định dạng ISO 8601)

Ví dụ:
Input: "Tạo task fix bug cho Alice trên Jira, deadline 20/12"
Output: {{
  "title": "Fix bug", 
  "platform": "jira",
  "assignees": ["alice"],
  "due_date": "2023-12-20T23:59:00"
}}

Câu lệnh thực tế: {user_input}
"""