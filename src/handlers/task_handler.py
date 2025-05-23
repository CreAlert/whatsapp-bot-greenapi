# src/handlers/task_handler.py
from datetime import datetime
# from typing import List, Dict # Tidak digunakan secara eksplisit di sini
from ..config import States, supabase
from ..utils import update_state_with_history, calculate_notification_times
# import asyncio # Tidak digunakan secara eksplisit di sini
import logging

# Setup timezone (sama seperti di worker dan admin_handler)
try:
    from zoneinfo import ZoneInfo
    # utc_tz = ZoneInfo("UTC") # Tidak perlu utc_tz di sini jika semua input/output adalah WIB
    indonesia_tz = ZoneInfo("Asia/Jakarta")
except ImportError:
    import pytz
    # utc_tz = pytz.utc
    indonesia_tz = pytz.timezone("Asia/Jakarta")

logger = logging.getLogger(__name__)

class TaskHandler:
    def __init__(self, bot):
        self.bot = bot
        # Pindahkan setup_handlers ke akhir __init__ atau panggil setelah semua atribut siap jika ada dependensi
        self.setup_handlers() 
        logger.info("TaskHandler initialized and handlers set up.")

    def _display_initial_menu(self, notification):
        """Helper untuk menampilkan menu utama."""
        logger.info(f"_display_initial_menu: Displaying for {notification.sender}")
        notification.answer(
            "*Hi, Skremates!* 💸\n\n"
            "Selamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\n"
            "Apa yang ingin kamu akses?\n\n"
            "1. Lihat Tugas\n"
            "2. Panel Ketua Kelas\n\n"
            "Ketik angka pilihan kamu *(1-2)*"
        )
        # Reset history saat kembali ke menu utama dari alur tugas
        notification.state_manager.update_state_data(notification.sender, {"state_history": []})
        notification.state_manager.update_state(notification.sender, States.INITIAL)

    def _display_class_selection_menu(self, notification, prefix_message=""):
        """Helper untuk menampilkan menu pemilihan kelas."""
        logger.info(f"_display_class_selection_menu: Called for {notification.sender}")
        try:
            response = supabase.table('classes').select('id, name').order('id').execute()
            if hasattr(response, 'error') and response.error:
                logger.error(f"_display_class_selection_menu: Supabase error fetching classes: {response.error}")
                notification.answer(prefix_message + "Terjadi error saat mengambil daftar kelas.")
                return False # Indikasi gagal

            classes_data = response.data
            if not classes_data:
                logger.warning("_display_class_selection_menu: No classes found.")
                notification.answer(prefix_message + "Maaf, belum ada daftar kelas yang tersedia.")
                return False # Indikasi gagal
            
            class_list_str = "\n".join([f"{item['id']}. {item['name']}" for item in classes_data])
            message = (
                prefix_message +
                "🧑‍🏫 *Pilih Kelasmu:* 👩‍🏫\n\n"
                f"{class_list_str}\n\n"
                "_Note:_\n"
                "Ketik angka sesuai pilihan kelasmu.\n"
                "Ketik 0 untuk kembali ke Menu Utama."
            )
            notification.answer(message)
            return True # Indikasi sukses
        except Exception as e:
            logger.error(f"_display_class_selection_menu: Exception: {e}", exc_info=True)
            notification.answer(prefix_message + "Terjadi error sistem saat menampilkan pilihan kelas.")
            return False


    def _display_day_selection_menu(self, notification, prefix_message=""):
        """Helper untuk menampilkan menu pemilihan hari."""
        logger.info(f"_display_day_selection_menu: Called for {notification.sender}")
        try:
            days_response = supabase.table('days').select('id, name').order('id').execute()
            if hasattr(days_response, 'error') and days_response.error:
                logger.error(f"_display_day_selection_menu: Supabase error fetching days: {days_response.error}")
                notification.answer(prefix_message + "Terjadi error saat mengambil daftar hari.")
                return False

            days_data = days_response.data
            if not days_data:
                logger.warning("_display_day_selection_menu: No days found.")
                notification.answer(prefix_message + "Maaf, belum ada daftar hari yang tersedia.")
                return False
                
            day_list_str = "\n".join([f"{item['id']}. {item['name']}" for item in days_data])
            message = (
                prefix_message +
                "🗓️ *Pilih Hari Pengumpulan Tugas:* 🗓️\n\n"
                f"{day_list_str}\n\n"
                "_Note:_\n"
                "Ketik angka sesuai pilihan hari.\n"
                "Ketik 0 untuk kembali ke Pilihan Kelas."
            )
            notification.answer(message)
            return True
        except Exception as e:
            logger.error(f"_display_day_selection_menu: Exception: {e}", exc_info=True)
            notification.answer(prefix_message + "Terjadi error sistem saat menampilkan pilihan hari.")
            return False

    def setup_handlers(self):
        logger.info("TaskHandler: Setting up message handlers.")

        @self.bot.router.message(type_message="textMessage", state=States.CLASS_SELECTION)
        def class_selection_state_handler(notification):
            logger.info(f"CLASS_SELECTION_STATE_HANDLER: Received '{notification.message_text}' from {notification.sender}")
            if notification.message_text == "0":
                logger.info("CLASS_SELECTION_STATE_HANDLER: User chose 0, returning to initial menu.")
                self._display_initial_menu(notification) # Panggil helper menu utama
            # Validasi input kelas (misal, ID kelas adalah angka 1-8)
            elif notification.message_text.isdigit() and 1 <= int(notification.message_text) <= 8: # Sesuaikan range jika perlu
                self.class_selection_handler(notification)
            else:
                self.show_invalid_message(notification, States.CLASS_SELECTION)

        @self.bot.router.message(type_message="textMessage", state=States.DAY_SELECTION)
        def day_selection_state_handler(notification):
            logger.info(f"DAY_SELECTION_STATE_HANDLER: Received '{notification.message_text}' from {notification.sender}")
            if notification.message_text == "0":
                logger.info("DAY_SELECTION_STATE_HANDLER: User chose 0, returning to class selection.")
                self.start_flow_handler(notification) # Kembali untuk memilih kelas lagi
            # Validasi input hari (misal, ID hari adalah angka 1-7)
            elif notification.message_text.isdigit() and 1 <= int(notification.message_text) <= 7: # Sesuaikan range jika perlu
                self.day_selection_handler(notification)
            else:
                self.show_invalid_message(notification, States.DAY_SELECTION)

        @self.bot.router.message(type_message="textMessage", state=States.TASK_LIST)
        def task_list_state_handler(notification):
            logger.info(f"TASK_LIST_STATE_HANDLER: Received '{notification.message_text}' from {notification.sender}")
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            if notification.message_text == "0":
                logger.info("TASK_LIST_STATE_HANDLER: User chose 0, returning to day selection.")
                # Untuk kembali ke pemilihan hari, panggil class_selection_handler dengan class_id yang tersimpan
                selected_class_id = state_data.get("selected_class_id")
                if selected_class_id:
                    # Buat objek notifikasi sementara untuk mensimulasikan input pengguna
                    temp_notif = type('TempNotif', (), {
                        'sender': notification.sender, 
                        'message_text': selected_class_id,
                        'state_manager': notification.state_manager # Penting untuk akses state lebih lanjut
                    })()
                    self.class_selection_handler(temp_notif)
                else: # Fallback jika state tidak ada
                    self.start_flow_handler(notification)
            elif notification.message_text.isdigit():
                tasks = state_data.get("tasks", [])
                try:
                    task_idx = int(notification.message_text) - 1
                    if 0 <= task_idx < len(tasks):
                        self.task_detail_handler(notification)
                    else:
                        self.show_invalid_message(notification, States.TASK_LIST)
                except ValueError:
                    self.show_invalid_message(notification, States.TASK_LIST)
            else:
                self.show_invalid_message(notification, States.TASK_LIST)

        @self.bot.router.message(type_message="textMessage", state=States.NOTIFICATION_SETUP)
        def notification_setup_state_handler(notification):
            logger.info(f"NOTIFICATION_SETUP_STATE_HANDLER: Received '{notification.message_text}' from {notification.sender}")
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            if notification.message_text == "0":
                logger.info("NOTIFICATION_SETUP_STATE_HANDLER: User chose 0, returning to task list.")
                # Untuk kembali ke daftar tugas, panggil day_selection_handler dengan day_id yang tersimpan
                selected_day_id = state_data.get("selected_day_id")
                selected_class_id = state_data.get("selected_class_id") # Juga dibutuhkan oleh day_selection_handler
                if selected_day_id and selected_class_id:
                     # Perlu memastikan state "selected_class_id" ada sebelum memanggil day_selection_handler
                    temp_notif = type('TempNotif', (), {
                        'sender': notification.sender,
                        'message_text': selected_day_id, # Ini input untuk day_selection_handler
                        'state_manager': notification.state_manager
                    })()
                    # Pastikan selected_class_id ada di state sebelum memanggil day_selection_handler
                    notification.state_manager.update_state_data(notification.sender, {"selected_class_id": selected_class_id, "state_history": state_data.get("state_history", [])})
                    self.day_selection_handler(temp_notif)
                else: # Fallback
                    self.start_flow_handler(notification)
            elif notification.message_text == "1": # YA, ATUR REMINDER
                logger.info("NOTIFICATION_SETUP_STATE_HANDLER: User selected 1 (Yes, set reminder).")
                notification.answer("⏳ *Mengatur reminder...*\n\nMohon tunggu sebentar...")
                
                task = state_data.get("selected_task")
                if not task or not all(k in task for k in ['id', 'due_date', 'name']):
                    logger.error(f"NOTIFICATION_SETUP_STATE_HANDLER: Invalid/incomplete task data: {task}")
                    notification.answer("❌ Terjadi kesalahan: Data tugas tidak lengkap.")
                    return
                
                try:
                    due_date_utc = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                    notify_times_utc_iso = calculate_notification_times(due_date_utc) 
                    
                    insert_payload = {
                        "phone_number": notification.sender, "task_id": task['id'],
                        "notification_times": notify_times_utc_iso, "is_sent": False
                    }
                    logger.info(f"Attempting to insert notification: {insert_payload}")
                    response = supabase.table('notifications').insert(insert_payload).execute()
                    
                    if hasattr(response, 'error') and response.error:
                        logger.error(f"Supabase error saving notification: {response.error}")
                        notification.answer(f"❌ *Gagal menyimpan notifikasi ke DB*\nError: {response.error.message if hasattr(response.error, 'message') else response.error}")
                    elif response.data:
                        logger.info(f"Reminder successfully set for task ID {task['id']}.")
                        notification.answer(f"✅ *Reminder berhasil diatur!*\n\nKamu akan menerima reminder untuk tugas:\n📝 {task.get('name', 'N/A')}\n\nReminder akan dikirim:\n- 3 hari sebelum\n- 1 hari sebelum\n- 1 jam sebelum")
                        self._display_initial_menu(notification)
                    else:
                        logger.warning(f"Failed to save notification, no data/error in response: {response}")
                        notification.answer("❌ *Gagal menyimpan notifikasi (unknown DB issue)*\nSilakan coba lagi.")
                except Exception as e:
                    logger.error(f"Python exception saving notification: {e}", exc_info=True)
                    notification.answer("❌ *Terjadi kesalahan sistem saat mengatur reminder.*")
            elif notification.message_text == "2": # TIDAK
                self.skip_reminder_handler(notification)
            else:
                self.show_invalid_message(notification, States.NOTIFICATION_SETUP)


    def start_flow_handler(self, notification):
        logger.info(f"START_FLOW_HANDLER: Called by {notification.sender}")
        if self._display_class_selection_menu(notification):
            # Bersihkan state data spesifik alur tugas sebelumnya, hanya pertahankan history
            current_state_data = notification.state_manager.get_state_data(notification.sender) or {}
            history = current_state_data.get("state_history", [])
            clean_flow_state = {"state_history": history} # Hanya history yang dipertahankan saat memulai alur baru
            notification.state_manager.update_state_data(notification.sender, clean_flow_state)
            update_state_with_history(notification, States.CLASS_SELECTION)

    def class_selection_handler(self, notification):
        selected_class_id_str = notification.message_text
        logger.info(f"CLASS_SELECTION_HANDLER: User {notification.sender} selected class ID string '{selected_class_id_str}'")
        
        # Simpan ID kelas yang dipilih (sebagai string)
        current_state_data = notification.state_manager.get_state_data(notification.sender) or {}
        history = current_state_data.get("state_history", [])
        updated_flow_data = {
            "selected_class_id": selected_class_id_str,
            "state_history": history
            # Kosongkan state lain dari alur ini jika perlu (misal selected_day_id, tasks)
            # "selected_day_id": None, 
            # "tasks": [] 
        }
        notification.state_manager.update_state_data(notification.sender, updated_flow_data)
        logger.info(f"CLASS_SELECTION_HANDLER: State updated for {notification.sender} with selected_class_id: {selected_class_id_str}")
        
        if self._display_day_selection_menu(notification):
            update_state_with_history(notification, States.DAY_SELECTION)


    def day_selection_handler(self, notification):
        selected_day_id_str = notification.message_text
        logger.info(f"DAY_SELECTION_HANDLER: User {notification.sender} selected day ID string '{selected_day_id_str}'")
        
        try:
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            selected_class_id_str = state_data.get("selected_class_id")

            if not selected_class_id_str:
                logger.error(f"DAY_SELECTION_HANDLER: selected_class_id NOT FOUND in state for {notification.sender}.")
                notification.answer("Terjadi kesalahan: Kelas belum dipilih dengan benar. Silakan ulangi dari awal.")
                self.start_flow_handler(notification)
                return

            try:
                class_id_for_query = int(selected_class_id_str)
                day_id_for_query = int(selected_day_id_str)
            except ValueError:
                logger.error(f"DAY_SELECTION_HANDLER: Invalid class/day ID format. Class: '{selected_class_id_str}', Day: '{selected_day_id_str}'")
                notification.answer("Format ID kelas atau hari tidak valid. Silakan ulangi.")
                self.start_flow_handler(notification)
                return
            
            logger.info(f"DAY_SELECTION_HANDLER: Querying tasks for class_id: {class_id_for_query}, day_id: {day_id_for_query}")
            
            day_name_response = supabase.table('days').select('name').eq('id', day_id_for_query).maybe_single().execute()
            day_name = day_name_response.data['name'] if day_name_response.data else f"ID Hari {day_id_for_query}"

            # PERBAIKAN PENTING: Pastikan hanya mengambil kolom yang diperlukan dari tabel terkait
            tasks_response = supabase.table('tasks') \
                .select('id, name, description, due_date, jenis_tugas, class_id, day_id') \
                .eq('class_id', class_id_for_query) \
                .eq('day_id', day_id_for_query) \
                .order('due_date') \
                .execute()

            if hasattr(tasks_response, 'error') and tasks_response.error:
                logger.error(f"DAY_SELECTION_HANDLER: Supabase error fetching tasks: {tasks_response.error}")
                notification.answer("Terjadi error saat mengambil daftar tugas.")
                return

            tasks_data = tasks_response.data
            logger.info(f"DAY_SELECTION_HANDLER: Found {len(tasks_data)} tasks for class {class_id_for_query} day {day_id_for_query}. Data: {tasks_data}")

            if not tasks_data:
                notification.answer(f"📭 Yeay! Tidak ada tugas untuk kelas yang dipilih pada hari {day_name}.")
                self.class_selection_handler(type('TempNotif', (), {'sender': notification.sender, 'message_text': selected_class_id_str, 'state_manager': notification.state_manager})())
                return
            
            history = state_data.get("state_history", [])
            notification.state_manager.update_state_data(
                notification.sender, {
                    "tasks": tasks_data, "selected_day_id": selected_day_id_str,
                    "selected_class_id": selected_class_id_str, "state_history": history
                })
            logger.info(f"DAY_SELECTION_HANDLER: State updated with tasks for {notification.sender}.")
            
            tasks_list_display = []
            for idx, task in enumerate(tasks_data, 1):
                due_date_utc = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                due_date_wib = due_date_utc.astimezone(indonesia_tz)
                due_date_display = due_date_wib.strftime('%d/%m/%Y %H:%M WIB')
                tasks_list_display.append(f"{idx}. {task.get('name', 'N/A')}\n🗒️ {task.get('description', 'N/A')}\n⏰ {due_date_display}")
            
            message = (f"📚 *Tugas untuk hari {day_name}*:\n\n" + "\n\n".join(tasks_list_display) +
                       "\n\n_Note:_\nKetik angka tugas untuk detail & reminder.\nKetik 0 untuk kembali ke Pilihan Hari.")    
            notification.answer(message)
            update_state_with_history(notification, States.TASK_LIST)
            
        except Exception as e:
            logger.error(f"DAY_SELECTION_HANDLER: Exception: {e}", exc_info=True)
            notification.answer("Terjadi error sistem saat memproses pilihan hari.")

    def task_detail_handler(self, notification):
        selected_task_index_str = notification.message_text
        logger.info(f"TASK_DETAIL_HANDLER: User {notification.sender} selected task index str '{selected_task_index_str}'")
        try:
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            tasks_in_state = state_data.get("tasks", [])
            
            task_idx_chosen = int(selected_task_index_str) - 1

            if not (0 <= task_idx_chosen < len(tasks_in_state)):
                logger.warning(f"TASK_DETAIL_HANDLER: Index {task_idx_chosen} out of bounds.")
                self.show_invalid_message(notification, States.TASK_LIST)
                return
                
            selected_task_data = tasks_in_state[task_idx_chosen]
            logger.info(f"TASK_DETAIL_HANDLER: Displaying detail for task: {selected_task_data}")
            
            due_date_utc = datetime.fromisoformat(selected_task_data['due_date'].replace('Z', '+00:00'))
            due_date_wib = due_date_utc.astimezone(indonesia_tz)
            due_date_display = due_date_wib.strftime('%d/%m/%Y %H:%M WIB')
            
            message = (
                f"📚 *Detail Tugas:*\n\n"
                f"📝 *Nama:* {selected_task_data.get('name', 'N/A')}\n"
                f"📖 *Deskripsi:* {selected_task_data.get('description', 'N/A')}\n"
                f"⏰ *Deadline:* {due_date_display}\n"
                f"📂 *Jenis:* {selected_task_data.get('jenis_tugas', 'N/A').capitalize()}\n\n"
                "Apakah ingin diingatkan untuk tugas ini?\n1. ✅ Ya\n2. ❌ Tidak\n0. Kembali ke Daftar Tugas."
            )
            
            history = state_data.get("state_history", [])
            notification.state_manager.update_state_data(
                notification.sender, {
                    "selected_task": selected_task_data, "tasks": tasks_in_state, 
                    "selected_day_id": state_data.get("selected_day_id"), 
                    "selected_class_id": state_data.get("selected_class_id"), 
                    "state_history": history
                })
            update_state_with_history(notification, States.NOTIFICATION_SETUP)
            notification.answer(message)
        except Exception as e:
            logger.error(f"TASK_DETAIL_HANDLER: Exception: {e}", exc_info=True)
            notification.answer("Terjadi error sistem saat menampilkan detail tugas.")

    def skip_reminder_handler(self, notification):
        logger.info(f"SKIP_REMINDER_HANDLER: User {notification.sender} chose not to set reminder.")
        notification.answer("ℹ️ Tidak ada reminder yang diatur untuk tugas ini.")
        self._display_initial_menu(notification)

    def show_invalid_message(self, notification, current_state: str):
        logger.warning(f"SHOW_INVALID_MESSAGE: Invalid input by {notification.sender} in state {current_state}. Text: '{notification.message_text}'")
        prefix = "⚠️ *Input tidak valid!*\n\n"
        
        if current_state == States.CLASS_SELECTION:
            self._display_class_selection_menu(notification, prefix_message=prefix)
        elif current_state == States.DAY_SELECTION:
            self._display_day_selection_menu(notification, prefix_message=prefix)
        elif current_state == States.TASK_LIST:
            # Tampilkan ulang daftar tugas dari state
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            tasks = state_data.get("tasks", [])
            day_id = state_data.get("selected_day_id")
            day_name = "hari terpilih"
            if day_id:
                day_resp = supabase.table('days').select('name').eq('id', int(day_id)).maybe_single().execute()
                if day_resp.data: day_name = day_resp.data['name']
            
            if tasks:
                tasks_list_str = []
                for idx, task_item in enumerate(tasks, 1):
                    due_utc = datetime.fromisoformat(task_item['due_date'].replace('Z', '+00:00'))
                    due_wib_str = due_utc.astimezone(indonesia_tz).strftime('%d/%m/%Y %H:%M WIB')
                    tasks_list_str.append(f"{idx}. {task_item.get('name','N/A')}\n🗒️ {task_item.get('description','N/A')}\n⏰ {due_wib_str}")
                notification.answer(prefix + f"📚 *Tugas untuk hari {day_name}*:\n\n" + "\n\n".join(tasks_list_str) +
                                    "\n\n_Note:_\nKetik angka tugas...\nKetik 0 untuk kembali.")
            else:
                notification.answer(prefix + "Tidak ada tugas untuk ditampilkan ulang.")

        elif current_state == States.NOTIFICATION_SETUP:
            # Tampilkan ulang detail tugas dari state
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            task = state_data.get("selected_task")
            if task:
                due_utc = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                due_wib_str = due_utc.astimezone(indonesia_tz).strftime('%d/%m/%Y %H:%M WIB')
                notification.answer(
                    prefix + f"📚 *Detail Tugas:*\n\n📝 *Nama:* {task.get('name','N/A')}\n📖 *Deskripsi:* {task.get('description','N/A')}\n"
                    f"⏰ *Deadline:* {due_wib_str}\n📂 *Jenis:* {task.get('jenis_tugas','N/A').capitalize()}\n\n"
                    "Apakah ingin diingatkan untuk tugas ini?\n1. ✅ Ya\n2. ❌ Tidak\n0. Kembali."
                )
            else:
                notification.answer(prefix + "Detail tugas tidak ditemukan. Silakan ulangi.")
        else: # Fallback ke menu utama jika state tidak dikenali untuk invalid message
             self._display_initial_menu(notification)