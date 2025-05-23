# bot.py
import os
import logging
import asyncio
from whatsapp_chatbot_python import GreenAPIBot
from src.config import States
from src.handlers.task_handler import TaskHandler
from src.handlers.admin_handler import AdminHandler
from src.workers.notification_worker import NotificationWorker
# Hapus impor update_state_with_history jika tidak digunakan langsung di bot.py
# from src.utils import update_state_with_history 

# Initialize logger
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
print(f"### PYPRINT ### bot.py: Module loaded. Logger: {logger.name}")

# Variabel global untuk instances, akan diisi di main()
bot_instance = None
task_handler_instance = None # Nama variabel diubah agar tidak konflik dengan nama kelas
admin_handler_instance = None # Nama variabel diubah
notification_worker_instance = None # Nama variabel diubah

async def main():
    global bot_instance, task_handler_instance, admin_handler_instance, notification_worker_instance

    print(f"### PYPRINT ### bot.py main(): Function started.")
    logger.info("Main function started.")
    
    GREENAPI_ID = os.getenv("GREENAPI_ID")
    GREENAPI_TOKEN = os.getenv("GREENAPI_TOKEN")

    if not GREENAPI_ID or not GREENAPI_TOKEN:
        print("### PYPRINT FATAL ### bot.py main(): GREENAPI_ID or GREENAPI_TOKEN not set!")
        logger.critical("GREENAPI_ID or GREENAPI_TOKEN not set! Bot cannot start properly.")
        return

    bot_instance = GreenAPIBot(
        GREENAPI_ID,
        GREENAPI_TOKEN,
        settings={
            "delaySendMessagesMilliseconds": 500,
            "markIncomingMessagesReaded": "yes",
            "incomingWebhook": "yes",
        }
    )
    print(f"### PYPRINT ### bot.py main(): GreenAPIBot initialized.")
    logger.info("GreenAPIBot initialized.")

    try:
        task_handler_instance = TaskHandler(bot_instance)
        admin_handler_instance = AdminHandler(bot_instance)
        print("### PYPRINT ### bot.py main(): TaskHandler and AdminHandler initialized.")
        logger.info("TaskHandler and AdminHandler initialized.")
    except Exception as e_handler_init:
        print(f"### PYPRINT ERROR ### bot.py main(): Error initializing handlers: {e_handler_init}")
        logger.error(f"Error initializing handlers: {e_handler_init}", exc_info=True)

    try:
        notification_worker_instance = NotificationWorker(bot_instance)
        print("### PYPRINT ### bot.py main(): NotificationWorker class instantiated.")
        logger.info("NotificationWorker class instantiated.")
    except Exception as e_worker_init:
        print(f"### PYPRINT ERROR ### bot.py main(): Error instantiating NotificationWorker: {e_worker_init}")
        logger.error(f"Error instantiating NotificationWorker: {e_worker_init}", exc_info=True)
    
    # --- SETUP ROUTER MESSAGE (DARI KODE LAMA ANDA) ---
    # Menggunakan bot_instance yang sudah diinisialisasi
    @bot_instance.router.message(type_message="textMessage", state=None)
    def initial_handler(notification):
        logger.info(f"initial_handler called by {notification.sender}")
        notification.answer("*Hi, Skremates!* 💸\n\nSelamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\nApa yang ingin kamu akses?\n\n1. Lihat Tugas\n2. Panel Ketua Kelas\n\nKetik angka pilihan kamu *(1-2)*")
        notification.state_manager.update_state_data(notification.sender, {"state_history": []})
        notification.state_manager.update_state(notification.sender, States.INITIAL)

    @bot_instance.router.message(type_message="textMessage", state=States.INITIAL)
    def initial_state_handler(notification):
        logger.info(f"initial_state_handler called by {notification.sender} with text: {notification.message_text}")
        if notification.message_text == "1":
            if task_handler_instance: task_handler_instance.start_flow_handler(notification)
            else: logger.warning("task_handler_instance not available for option 1")
        elif notification.message_text == "2":
            if admin_handler_instance: admin_handler_instance.admin_menu_handler(notification)
            else: logger.warning("admin_handler_instance not available for option 2")
        elif notification.message_text == "0":
            notification.answer("Kamu sudah berada di menu utama")
        else:
            notification.answer("⚠️ *Input tidak valid!*\n\n*Hi, Skremates!* 💸\n\nSelamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\nApa yang ingin kamu akses?\n\n1. Lihat Tugas\n2. Panel Ketua Kelas\n\nKetik angka pilihan kamu *(1-2)*")

    @bot_instance.router.message(type_message="textMessage", regexp=r"^(menu)$")
    def menu_handler(notification):
        logger.info(f"menu_handler called by {notification.sender}")
        initial_handler(notification)

    @bot_instance.router.message(type_message="textMessage", regexp=r"^0$")
    def global_back_handler(notification): # Pastikan semua handler di sini menggunakan instance yang benar
        logger.info(f"global_back_handler called by {notification.sender}")
        current_state = notification.state_manager.get_state(notification.sender)
        state_data = notification.state_manager.get_state_data(notification.sender) or {}
        state_history = state_data.get("state_history", [])
        if current_state == States.INITIAL:
            notification.answer("Kamu sudah berada di menu utama")
            return
        
        previous_state_val = state_history.pop() if state_history else States.INITIAL
        notification.state_manager.update_state_data(notification.sender, {"state_history": state_history})
        logger.info(f"Global back: from {current_state} to {previous_state_val}")

        if previous_state_val == States.INITIAL: initial_handler(notification)
        elif current_state == States.CLASS_SELECTION: initial_handler(notification) # Kembali dari Pilihan Kelas adalah Menu Utama
        elif current_state == States.DAY_SELECTION and task_handler_instance: task_handler_instance.start_flow_handler(notification) # Kembali dari Pilihan Hari ke Pilihan Kelas
        elif current_state == States.TASK_LIST and task_handler_instance: # Kembali dari Daftar Tugas ke Pilihan Hari
            class_id = state_data.get("selected_class_id")
            if class_id:
                temp_notif = type('TempNotif',(),{'sender': notification.sender, 'message_text': class_id, 'state_manager': notification.state_manager})()
                task_handler_instance.class_selection_handler(temp_notif)
            else: initial_handler(notification)
        elif current_state == States.NOTIFICATION_SETUP and task_handler_instance: # Kembali dari Setup Notif ke Daftar Tugas
            day_id = state_data.get("selected_day_id")
            class_id = state_data.get("selected_class_id")
            if day_id and class_id:
                notification.state_manager.update_state_data(notification.sender, {"selected_class_id": class_id, "state_history": state_history})
                temp_notif = type('TempNotif',(),{'sender': notification.sender, 'message_text': day_id, 'state_manager': notification.state_manager})()
                task_handler_instance.day_selection_handler(temp_notif)
            else: initial_handler(notification)
        elif current_state == States.ADMIN_MENU: initial_handler(notification)
        # Tambahkan kondisi untuk state ADMIN_ADD_TASK dan state admin lainnya jika perlu
        # elif current_state == States.ADMIN_ADD_TASK and admin_handler_instance: admin_handler_instance.admin_menu_handler(notification)
        else: initial_handler(notification)
    # --- AKHIR SETUP ROUTER MESSAGE ---

    worker_task = None 
    try:
        if notification_worker_instance: 
            print("### PYPRINT ### bot.py main(): Attempting to start NotificationWorker.")
            logger.info("Main: Attempting to start NotificationWorker.")
            worker_task = await notification_worker_instance.start() 
            print(f"### PYPRINT ### bot.py main(): NotificationWorker.start() returned. Task object: {worker_task}")
            logger.info(f"Main: NotificationWorker.start() returned. Task object: {worker_task}")

            if worker_task:
                print("### PYPRINT ### bot.py main(): Worker task exists. Adding 15s delay for observation...")
                logger.info("Main: Worker task exists. Adding 15 seconds delay for observation...")
                await asyncio.sleep(15) 
                print("### PYPRINT ### bot.py main(): 15s observation finished.")
                logger.info("Main: 15-second observation finished.")
                if worker_task.done():
                    logger.warning("Main: Worker task IS DONE during observation. UNEXPECTED. Check logs.")
                    try: await worker_task 
                    except Exception as e_wt_done: logger.error(f"Main: Exception from awaiting worker_task: {e_wt_done}", exc_info=True)
                else: logger.info("Main: Worker task is still running. Expected.")
            else:
                print("### PYPRINT ERROR ### bot.py main(): Worker task NOT created.")
                logger.error("Main: Worker task was NOT created. Check NotificationWorker.start() logs.")
        else:
            print("### PYPRINT WARNING ### bot.py main(): notification_worker_instance is None. Worker not started.")
            logger.warning("notification_worker_instance is None. Worker not started.")
        
        print("### PYPRINT ### bot.py main(): Starting GreenAPIBot event loop (bot.run_forever()).")
        logger.info("Main: Starting GreenAPIBot event loop (bot.run_forever()).")
        await bot_instance.run_forever() # Pastikan menggunakan bot_instance
            
    except KeyboardInterrupt:
        print("### PYPRINT ### bot.py main(): KeyboardInterrupt in main try block.")
        logger.info("Main: KeyboardInterrupt in main try block.")
    except Exception as e:
        print(f"### PYPRINT ERROR ### bot.py main(): Error in main execution: {e}")
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        print("### PYPRINT ### bot.py main(): Finally block reached.")
        logger.info("Main: Finally block reached. Attempting to stop notification worker.")
        if notification_worker_instance: 
            await notification_worker_instance.stop()
        logger.info("Main: Notification worker stop process initiated. Main function exiting.")
        print("### PYPRINT ### bot.py main(): Main function finally block finished.")

if __name__ == "__main__":
    print("### PYPRINT ### bot.py: Script execution started from __main__.")
    logger.info("Starting bot from __main__.")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("### PYPRINT ### bot.py: Bot (asyncio.run) stopped by KeyboardInterrupt.")
        logger.info("Bot (asyncio.run) stopped by user with KeyboardInterrupt.")
    except Exception as e_run_main:
        print(f"### PYPRINT ERROR ### bot.py: Bot (asyncio.run) fatal error: {e_run_main}")
        logger.error(f"Bot (asyncio.run) fatal error: {e_run_main}", exc_info=True)
    print("### PYPRINT ### bot.py: Script finished or exiting from __main__.")