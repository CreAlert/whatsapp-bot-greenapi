# bot.py
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
    level=logging.INFO, # Ganti ke logging.DEBUG jika ingin melihat log worker yang lebih detail
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
print(f"### PYPRINT ### bot.py: Module loaded. Logger name: {logger.name}")

# Inisialisasi global (akan diisi di __main__ atau fungsi setup jika ada)
# Ini untuk menghindari error jika diakses sebelum diinisialisasi di beberapa skenario
bot = None
task_handler = None
admin_handler = None
notification_worker = None

async def main():
    """Main function to run the bot and notification worker"""
    global bot, task_handler, admin_handler, notification_worker # Deklarasikan bahwa kita menggunakan variabel global

    print(f"### PYPRINT ### bot.py main(): Function started.")
    logger.info("Main function started.")
    
    # Initialize GreenAPI bot
    GREENAPI_ID = os.getenv("GREENAPI_ID")
    GREENAPI_TOKEN = os.getenv("GREENAPI_TOKEN")

    if not GREENAPI_ID or not GREENAPI_TOKEN:
        print("### PYPRINT FATAL ### bot.py main(): GREENAPI_ID or GREENAPI_TOKEN not set!")
        logger.critical("GREENAPI_ID or GREENAPI_TOKEN not set! Bot cannot start properly.")
        return # Keluar jika kredensial tidak ada

    bot = GreenAPIBot(
        GREENAPI_ID,
        GREENAPI_TOKEN,
        settings={
            "delaySendMessagesMilliseconds": 500,
            "markIncomingMessagesReaded": "yes",
            "incomingWebhook": "yes",
        }
    )
    print(f"### PYPRINT ### bot.py main(): GreenAPIBot initialized. ID: {str(GREENAPI_ID)[:5]}...")
    logger.info("GreenAPIBot initialized.")

    # Initialize handlers
    try:
        task_handler = TaskHandler(bot)
        admin_handler = AdminHandler(bot)
        print("### PYPRINT ### bot.py main(): TaskHandler and AdminHandler initialized.")
        logger.info("TaskHandler and AdminHandler initialized.")
    except Exception as e_handler_init:
        print(f"### PYPRINT ERROR ### bot.py main(): Error initializing handlers: {e_handler_init}")
        logger.error(f"Error initializing handlers: {e_handler_init}", exc_info=True)
        # Anda mungkin ingin keluar jika handler penting

    # Initialize notification worker
    try:
        notification_worker = NotificationWorker(bot)
        print("### PYPRINT ### bot.py main(): NotificationWorker class instantiated.")
        logger.info("NotificationWorker class instantiated.")
    except Exception as e_worker_init:
        print(f"### PYPRINT ERROR ### bot.py main(): Error instantiating NotificationWorker: {e_worker_init}")
        logger.error(f"Error instantiating NotificationWorker: {e_worker_init}", exc_info=True)
        # notification_worker akan tetap None, akan ditangani di bawah


    # Setup router message (salin dari kode lama Anda)
    @bot.router.message(type_message="textMessage", state=None)
    def initial_handler(notification):
        logger.info(f"initial_handler called by {notification.sender}")
        notification.answer("*Hi, Skremates!* 💸\n\nSelamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\nApa yang ingin kamu akses?\n\n1. Lihat Tugas\n2. Panel Ketua Kelas\n\nKetik angka pilihan kamu *(1-2)*")
        notification.state_manager.update_state_data(notification.sender, {"state_history": []})
        notification.state_manager.update_state(notification.sender, States.INITIAL)

    @bot.router.message(type_message="textMessage", state=States.INITIAL)
    def initial_state_handler(notification):
        logger.info(f"initial_state_handler called by {notification.sender} with text: {notification.message_text}")
        if notification.message_text == "1":
            if task_handler: task_handler.start_flow_handler(notification)
            else: logger.warning("task_handler not available in initial_state_handler for option 1")
        elif notification.message_text == "2":
            if admin_handler: admin_handler.admin_menu_handler(notification)
            else: logger.warning("admin_handler not available in initial_state_handler for option 2")
        elif notification.message_text == "0":
            notification.answer("Kamu sudah berada di menu utama")
        else:
            notification.answer("⚠️ *Input tidak valid!*\n\n*Hi, Skremates!* 💸\n\nSelamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\nApa yang ingin kamu akses?\n\n1. Lihat Tugas\n2. Panel Ketua Kelas\n\nKetik angka pilihan kamu *(1-2)*")

    @bot.router.message(type_message="textMessage", regexp=r"^(menu)$")
    def menu_handler(notification):
        logger.info(f"menu_handler called by {notification.sender}")
        initial_handler(notification)

    @bot.router.message(type_message="textMessage", regexp=r"^0$")
    def global_back_handler(notification):
        logger.info(f"global_back_handler called by {notification.sender}")
        current_state = notification.state_manager.get_state(notification.sender)
        state_data = notification.state_manager.get_state_data(notification.sender) or {}
        state_history = state_data.get("state_history", [])
        if current_state == States.INITIAL:
            notification.answer("Kamu sudah berada di menu utama")
            return
        previous_state = state_history.pop() if state_history else States.INITIAL
        notification.state_manager.update_state_data(notification.sender, {"state_history": state_history})
        logger.info(f"Global back: from {current_state} to {previous_state if previous_state else 'INITIAL'}")
        # Logika navigasi kembali (perlu disesuaikan dengan kebutuhan detail Anda)
        if previous_state == States.CLASS_SELECTION and task_handler : task_handler.start_flow_handler(notification)
        elif previous_state == States.DAY_SELECTION and task_handler : task_handler.class_selection_handler(notification) # Mungkin perlu fungsi display_class_menu
        elif previous_state == States.TASK_LIST and task_handler : task_handler.day_selection_handler(notification) # Mungkin perlu fungsi display_day_menu
        elif previous_state == States.NOTIFICATION_SETUP and task_handler : task_handler.task_detail_handler(notification) # Mungkin perlu fungsi display_task_list
        elif previous_state == States.ADMIN_MENU and admin_handler : initial_handler(notification) # Atau admin_handler.show_main_admin_menu()
        # ... (tambahkan kondisi lain)
        else: initial_handler(notification)


    worker_task = None 
    try:
        if notification_worker: # Hanya start jika worker berhasil diinisialisasi
            print("### PYPRINT ### bot.py main(): Attempting to start NotificationWorker.")
            logger.info("Main: Attempting to start NotificationWorker.")
            worker_task = await notification_worker.start() 
            print(f"### PYPRINT ### bot.py main(): NotificationWorker.start() returned. Task object: {worker_task}")
            logger.info(f"Main: NotificationWorker.start() returned. Task object: {worker_task}")

            if worker_task:
                print("### PYPRINT ### bot.py main(): Worker task object exists. Adding 15s delay to observe worker logs...")
                logger.info("Main: Worker task object exists. Adding 15 seconds delay to observe worker logs...")
                await asyncio.sleep(15) # Beri waktu worker untuk log siklus pertamanya
                print("### PYPRINT ### bot.py main(): 15s observation period finished.")
                logger.info("Main: 15-second observation period finished.")
                if worker_task.done():
                    logger.warning("Main: Worker task IS DONE during observation. This is UNEXPECTED. Check worker logs.")
                    try: await worker_task 
                    except Exception as e_wt_done: logger.error(f"Main: Exception from awaiting completed worker_task: {e_wt_done}", exc_info=True)
                else: logger.info("Main: Worker task is still running (not done). This is expected.")
            else:
                print("### PYPRINT ERROR ### bot.py main(): Worker task was NOT created.")
                logger.error("Main: Worker task was NOT created (worker_task is None). Check NotificationWorker.start() logs.")
        else:
            print("### PYPRINT WARNING ### bot.py main(): notification_worker object is None. Worker not started.")
            logger.warning("notification_worker object is None. Worker not started.")
        
        print("### PYPRINT ### bot.py main(): Starting GreenAPIBot event loop (bot.run_forever()).")
        logger.info("Main: Starting GreenAPIBot event loop (bot.run_forever()).")
        await bot.run_forever() # Jalankan bot utama untuk menerima pesan
            
    except KeyboardInterrupt: # Tangkap Ctrl+C di sini juga
        print("### PYPRINT ### bot.py main(): KeyboardInterrupt received in main try block.")
        logger.info("Main: KeyboardInterrupt received in main try block.")
    except Exception as e:
        print(f"### PYPRINT ERROR ### bot.py main(): Error in main execution: {e}")
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        print("### PYPRINT ### bot.py main(): Finally block reached.")
        logger.info("Main: Finally block reached. Attempting to stop notification worker.")
        if notification_worker: # Cek lagi sebelum stop
            await notification_worker.stop()
        logger.info("Main: Notification worker stop process initiated. Main function exiting.")
        print("### PYPRINT ### bot.py main(): Main function finally block finished.")

if __name__ == "__main__":
    print("### PYPRINT ### bot.py: Script execution started from __main__.")
    logger.info("Starting bot from __main__.")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("### PYPRINT ### bot.py: Bot (asyncio.run) stopped by user with KeyboardInterrupt.")
        logger.info("Bot (asyncio.run) stopped by user with KeyboardInterrupt.")
    except Exception as e_run_main:
        print(f"### PYPRINT ERROR ### bot.py: Bot (asyncio.run) fatal error: {e_run_main}")
        logger.error(f"Bot (asyncio.run) fatal error: {e_run_main}", exc_info=True)
    print("### PYPRINT ### bot.py: Script finished or exiting due to error from __main__.")