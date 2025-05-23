# bot.py
import os
import logging
import asyncio
from whatsapp_chatbot_python import GreenAPIBot
# Pastikan path impor ini benar sesuai struktur folder Anda
from src.config import States 
from src.handlers.task_handler import TaskHandler 
from src.handlers.admin_handler import AdminHandler
from src.workers.notification_worker import NotificationWorker
from src.utils import update_state_with_history

# Initialize logger (pastikan levelnya INFO atau DEBUG)
logging.basicConfig(
    level=logging.INFO, # Ganti ke logging.DEBUG untuk log yang lebih detail dari worker
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
print("### PYPRINT ### bot.py: Module loaded, logger configured.")

# Load environment variables jika Anda menggunakan python-dotenv dan file .env
# (Biasanya di Render, env vars diatur di dashboardnya langsung)
# try:
#     from dotenv import load_dotenv
#     load_dotenv()
#     print("### PYPRINT ### bot.py: .env loaded (if python-dotenv is used).")
#     logger.info("bot.py: .env loaded.")
# except ImportError:
#     print("### PYPRINT ### bot.py: python-dotenv not installed, skipping .env load.")
#     logger.info("bot.py: python-dotenv not installed, skipping .env load.")


# Initialize GreenAPI bot
GREENAPI_ID = os.getenv("GREENAPI_ID")
GREENAPI_TOKEN = os.getenv("GREENAPI_TOKEN")

if not GREENAPI_ID or not GREENAPI_TOKEN:
    print("### PYPRINT FATAL ### GREENAPI_ID or GREENAPI_TOKEN not set in environment variables!")
    logger.critical("GREENAPI_ID or GREENAPI_TOKEN not set in environment variables! Bot cannot start.")
    # exit(1) # Sebaiknya keluar jika kredensial tidak ada

bot = GreenAPIBot(
    GREENAPI_ID,
    GREENAPI_TOKEN,
    settings={
        "delaySendMessagesMilliseconds": 500,
        "markIncomingMessagesReaded": "yes",
        "incomingWebhook": "yes", # Pastikan webhook sudah diatur di GreenAPI & URL-nya benar jika Render adalah Web Service
    }
)
print(f"### PYPRINT ### bot.py: GreenAPIBot initialized. ID: {GREENAPI_ID[:5]}...") # Cetak sebagian ID
logger.info("GreenAPIBot initialized.")

# Initialize handlers
# Untuk tes worker, Anda bisa komentari inisialisasi handler jika mereka kompleks atau mungkin error
try:
    task_handler = TaskHandler(bot)
    admin_handler = AdminHandler(bot)
    print("### PYPRINT ### bot.py: TaskHandler and AdminHandler initialized.")
    logger.info("TaskHandler and AdminHandler initialized.")
except Exception as e_handler_init:
    print(f"### PYPRINT ERROR ### bot.py: Error initializing handlers: {e_handler_init}")
    logger.error(f"Error initializing handlers: {e_handler_init}", exc_info=True)
    # Mungkin Anda ingin keluar atau menangani ini jika handler penting
    # exit(1)


# Initialize notification worker
try:
    notification_worker = NotificationWorker(bot)
    print("### PYPRINT ### bot.py: NotificationWorker class instantiated.")
    logger.info("NotificationWorker class instantiated.")
except Exception as e_worker_init:
    print(f"### PYPRINT ERROR ### bot.py: Error instantiating NotificationWorker: {e_worker_init}")
    logger.error(f"Error instantiating NotificationWorker: {e_worker_init}", exc_info=True)
    notification_worker = None # Set ke None agar tidak error di finally block
    # exit(1)


# @bot.router.message(...) - Handler Anda yang sudah ada
# Anda bisa biarkan ini atau komentari sementara jika ingin fokus hanya pada worker
# (Kode router message Anda dari file lama diletakkan di sini)
@bot.router.message(
    type_message="textMessage",
    state=None
)
def initial_handler(notification):
    """Initial message with text menu"""
    logger.info(f"initial_handler called by {notification.sender}")
    notification.answer(
        "*Hi, Skremates!* 💸\n\n"
        "Selamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\n"
        
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
    logger.info(f"initial_state_handler called by {notification.sender} with text: {notification.message_text}")
    if notification.message_text == "1":
        if 'task_handler' in globals(): task_handler.start_flow_handler(notification)
        else: logger.warning("task_handler not initialized.")
    elif notification.message_text == "2":
        if 'admin_handler' in globals(): admin_handler.admin_menu_handler(notification)
        else: logger.warning("admin_handler not initialized.")
    elif notification.message_text == "0":
        notification.answer("Kamu sudah berada di menu utama")
    else:
        notification.answer(
            "⚠️ *Input tidak valid!*\n\n"
            # ... (pesan tidak valid Anda)
        )

@bot.router.message(
    type_message="textMessage",
    regexp=r"^(menu)$"
)
def menu_handler(notification):
    logger.info(f"menu_handler called by {notification.sender}")
    initial_handler(notification)

@bot.router.message(
    type_message="textMessage",
    regexp=r"^0$"
)
def global_back_handler(notification):
    logger.info(f"global_back_handler called by {notification.sender}")
    # ... (logika global_back_handler Anda) ...
    current_state = notification.state_manager.get_state(notification.sender)
    state_data = notification.state_manager.get_state_data(notification.sender) or {}
    state_history = state_data.get("state_history", [])
    
    if current_state == States.INITIAL:
        notification.answer("Kamu sudah berada di menu utama")
        return
    
    previous_state = state_history.pop() if state_history else States.INITIAL
    notification.state_manager.update_state_data(notification.sender, {"state_history": state_history})
    
    # Navigasi berdasarkan state sebelumnya atau kembali ke initial_handler
    # Ini perlu disesuaikan dengan logika handler Anda jika ingin kembali ke handler spesifik
    logger.info(f"Navigating back from {current_state} to {previous_state if previous_state != States.INITIAL else 'initial menu'}")
    if previous_state == States.CLASS_SELECTION and 'task_handler' in globals():
        task_handler.start_flow_handler(notification) # Ini akan menampilkan pilihan kelas lagi
    elif previous_state == States.DAY_SELECTION and 'task_handler' in globals():
        task_handler.class_selection_handler(notification) # Ini akan menampilkan pilihan hari lagi
    # Tambahkan kondisi lain atau default ke initial_handler
    else:
        initial_handler(notification)


async def main():
    """Main function to run the bot and notification worker"""
    print("### PYPRINT ### bot.py: main() function started.")
    logger.info("Main function started.")
    worker_task = None 
    try:
        if notification_worker:
            print("### PYPRINT ### bot.py main(): Attempting to start NotificationWorker.")
            logger.info("Main: Attempting to start NotificationWorker.")
            worker_task = await notification_worker.start() 
            print(f"### PYPRINT ### bot.py main(): NotificationWorker.start() returned. Task object: {worker_task}")
            logger.info(f"Main: NotificationWorker.start() returned. Task object: {worker_task}")

            if worker_task:
                print("### PYPRINT ### bot.py main(): Worker task object exists. Waiting for 30s to observe worker logs...")
                logger.info("Main: Worker task object exists. Waiting for 30 seconds to observe worker logs...")
                await asyncio.sleep(30) 
                print("### PYPRINT ### bot.py main(): 30s observation period finished.")
                logger.info("Main: 30-second observation period finished.")
                if worker_task.done():
                    logger.warning("Main: Worker task IS DONE during observation. This is UNEXPECTED. Check worker logs.")
                    try:
                        await worker_task # Coba await untuk memunculkan exception jika ada
                    except Exception as e_wt_done:
                        logger.error(f"Main: Exception from awaiting completed worker_task: {e_wt_done}", exc_info=True)
                else:
                    logger.info("Main: Worker task is still running (not done). This is expected.")
            else:
                print("### PYPRINT ERROR ### bot.py main(): Worker task was NOT created.")
                logger.error("Main: Worker task was NOT created (worker_task is None). Check NotificationWorker.start() logs.")
        else:
            print("### PYPRINT WARNING ### bot.py main(): notification_worker object is None. Worker not started.")
            logger.warning("notification_worker object is None. Worker not started.")


        print("### PYPRINT ### bot.py main(): Starting GreenAPIBot event loop (bot.run_forever()) - COMMENTED OUT FOR TEST.")
        logger.info("Main: Starting GreenAPIBot event loop (bot.run_forever()) - THIS WILL BE SKIPPED OR LIMITED FOR WORKER TEST.")
        
        # HANYA UNTUK TES WORKER, JANGAN GUNAKAN INI DI PRODUKSI JIKA BOT PERLU MENERIMA PESAN
        # Komentari `await bot.run_forever()` di bawah jika Anda HANYA ingin tes worker
        # await bot.run_forever() 
        # logger.info("Bot is running forever...")

        # Loop pengganti untuk menjaga main() tetap hidup selama tes worker (jika bot.run_forever() dikomentari)
        if worker_task and not worker_task.done():
             logger.info("Main: Entering TEST keep-alive loop while worker runs (bot.run_forever() is commented out).")
             print("### PYPRINT ### bot.py main(): Entering TEST keep-alive loop.")
             for i in range(24): # Tunggu sekitar 2 menit (24 * 5 detik = 120 detik)
                 if worker_task.done():
                     logger.info(f"Main: Worker task finished during keep-alive test loop (iteration {i+1}).")
                     print(f"### PYPRINT ### bot.py main(): Worker task finished during keep-alive test loop (iteration {i+1}).")
                     break
                 print(f"### PYPRINT ### bot.py main(): Test keep-alive loop, iteration {i+1}/24. Worker running: {not worker_task.done()}")
                 logger.debug(f"Main: Test keep-alive loop, iteration {i+1}/24. Worker running: {not worker_task.done()}")
                 await asyncio.sleep(5)
             logger.info("Main: Test keep-alive loop finished.")
             print("### PYPRINT ### bot.py main(): Test keep-alive loop finished.")
        else:
            logger.info("Main: Skipping keep-alive loop as worker task is done or not created.")
            print("### PYPRINT ### bot.py main(): Skipping keep-alive loop as worker task is done or not created.")

            
    except KeyboardInterrupt:
        print("### PYPRINT ### bot.py main(): KeyboardInterrupt received.")
        logger.info("Main: KeyboardInterrupt received.")
    except Exception as e:
        print(f"### PYPRINT ERROR ### bot.py main(): Error in main execution: {e}")
        logger.error(f"Main: Error in main execution: {e}", exc_info=True)
    finally:
        print("### PYPRINT ### bot.py main(): Finally block reached.")
        logger.info("Main: Finally block reached. Attempting to stop notification worker.")
        if 'notification_worker' in locals() and notification_worker: # Pastikan sudah didefinisikan
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