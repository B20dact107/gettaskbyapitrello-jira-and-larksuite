import asyncio
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from api.telegram_service import (
    TOKEN,
    start,
    username,
    show_tasks,
    create_issue,
    get_title,
    get_description,
    get_priority,
    get_assignees,
    get_platform,
    get_trello_board_name,
    get_trello_list_name,
    handle_jira_connection,
    get_jira_project_key,
    connect_platform,
    handle_platform_input,
    cancel,
    start_scheduler,
    # Import các state từ create_issue
    TITLE, DESCRIPTION, PRIORITY, ASSIGNEES, PLATFORM,
    # Import các state từ kết nối nền tảng
    PLATFORM_SELECTED, AWAITING_TRELLO_BOARD_NAME, AWAITING_TRELLO_LIST_NAME, AWAITING_JIRA_PROJECT_KEY
)

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Đăng ký command handlers
    conv_handler= ConversationHandler(
        entry_points= [CommandHandler("create_issue",create_issue)],
        states = {
            TITLE:        [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
            DESCRIPTION : [MessageHandler(filters.TEXT & ~filters.COMMAND , get_description)],
            PRIORITY :    [MessageHandler(filters.TEXT & ~ filters.COMMAND, get_priority)],
            ASSIGNEES:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_assignees)],
            PLATFORM:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_platform)]
        },
        fallbacks=[]
        
    )
    conv_auth = ConversationHandler(
    entry_points=[CommandHandler('connect', connect_platform)],
    states={
        PLATFORM_SELECTED: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_platform_input)],
        AWAITING_TRELLO_BOARD_NAME: [MessageHandler(filters.TEXT, get_trello_board_name)],
        AWAITING_TRELLO_LIST_NAME: [MessageHandler(filters.TEXT, get_trello_list_name)],
        AWAITING_JIRA_PROJECT_KEY: [MessageHandler(filters.TEXT, get_jira_project_key)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("username", username))
    application.add_handler(conv_auth)
    application.add_handler(CommandHandler("tasks", show_tasks))
    application.add_handler(conv_handler)
    
    start_scheduler()
    
    # Chạy bot ở chế độ polling (hoặc webhook)
    application.run_polling()

if __name__ == "__main__":
    run_bot()
