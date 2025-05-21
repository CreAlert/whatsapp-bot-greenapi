import os
import logging
import asyncio
from whatsapp_chatbot_python import GreenAPIBot
from src.config import States
from src.handlers.task_handler import TaskHandler
from src.handlers.admin_handler import AdminHandler
from src.workers.notification_worker import NotificationWorker
from src.utils import update_state_with_history

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize GreenAPI bot
bot = GreenAPIBot(
    os.getenv("GREENAPI_ID"),
    os.getenv("GREENAPI_TOKEN"),
    settings={
        "delaySendMessagesMilliseconds": 500,
        "markIncomingMessagesReaded": "yes",
        "incomingWebhook": "yes",
    }
)

# Initialize handlers
task_handler = TaskHandler(bot)
admin_handler = AdminHandler(bot)

# Initialize notification worker
notification_worker = NotificationWorker(bot)

@bot.router.message(
    type_message="textMessage",
    state=None
)
def initial_handler(notification):
    """Initial message with text menu"""
    notification.answer(
        "*Hi, Skremates!* 💸\n\n"
        "*Selamat datang di *Crealert: Your Weekly Task Reminder* 🔔!* \n\n"
        
        "Apa yang ingin kamu akses?\n\n"
        
        "1. Lihat Tugas\n"
        "2. Panel Ketua Kelas\n\n"
        "Ketik angka pilihan kamu *(1-2)*"
    )
    notification.state_manager.update_state_data(
        notification.sender,
        {"state_history": []}
    )
    notification.state_manager.update_state(
        notification.sender,
        States.INITIAL
    )

@bot.router.message(
    type_message="textMessage",
    state=States.INITIAL
)
def initial_state_handler(notification):
    """Handle all messages in INITIAL state"""
    if notification.message_text == "1":
        task_handler.start_flow_handler(notification)
    elif notification.message_text == "2":
        admin_handler.admin_menu_handler(notification)
    elif notification.message_text == "0":
        notification.answer("Kamu sudah berada di menu utama")
    else:
        notification.answer(
            "⚠️ *Input tidak valid!*\n\n"
            "*Hi, Skremates!* 💸\n\n"
            "*Selamat datang di *Crealert: Your Weekly Task Reminder* 🔔!* \n\n"
            
            "Apa yang ingin kamu akses?\n\n"
            
            "1. Lihat Tugas\n"
            "2. Panel Ketua Kelas\n\n"
            "Ketik angka pilihan kamu *(1-2)*"
        )

@bot.router.message(
    type_message="textMessage",
    regexp=r"^(menu)$"
)
def menu_handler(notification):
    """Handle menu command to return to initial state"""
    initial_handler(notification)

@bot.router.message(
    type_message="textMessage",
    regexp=r"^0$"
)
def global_back_handler(notification):
    """Handle back navigation for any state when typing 0"""
    current_state = notification.state_manager.get_state(notification.sender)
    state_data = notification.state_manager.get_state_data(notification.sender) or {}
    state_history = state_data.get("state_history", [])
    
    if current_state == States.INITIAL:
        notification.answer("Kamu sudah berada di menu utama")
        return
    
    # Get previous state from history
    previous_state = state_history.pop() if state_history else States.INITIAL
    
    # Update state data with new history
    notification.state_manager.update_state_data(
        notification.sender,
        {"state_history": state_history}
    )
    
    # Handle back navigation based on current state
    if current_state == States.CLASS_SELECTION:
        initial_handler(notification)
    elif current_state == States.DAY_SELECTION:
        task_handler.start_flow_handler(notification)
    elif current_state == States.TASK_LIST:
        state_data = notification.state_manager.get_state_data(notification.sender)
        selected_class_id = state_data.get("selected_class_id")
        task_handler.class_selection_handler(notification)
    elif current_state == States.NOTIFICATION_SETUP:
        state_data = notification.state_manager.get_state_data(notification.sender)
        selected_day_id = state_data.get("selected_day_id")
        task_handler.day_selection_handler(notification)
    elif current_state == States.ADMIN_MENU:
        initial_handler(notification)
    elif current_state == States.ADMIN_ADD_TASK:
        admin_handler.admin_menu_handler(notification)
    else:
        initial_handler(notification)

async def main():
    """Main function to run the bot and notification worker"""
    try:
        # Start notification worker
        worker_task = await notification_worker.start()
        
        # Start bot
        logger.info("Starting WhatsApp Task Bot")
        await bot.run_forever()
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        # Stop notification worker
        if notification_worker:
            await notification_worker.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")