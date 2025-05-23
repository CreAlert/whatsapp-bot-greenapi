# src/handlers/task_handler.py
from datetime import datetime
from ..config import States, supabase
from ..utils import update_state_with_history, calculate_notification_times # calculate_notification_times masih dipakai
import logging

try:
    from zoneinfo import ZoneInfo
    indonesia_tz = ZoneInfo("Asia/Jakarta")
except ImportError:
    import pytz
    indonesia_tz = pytz.timezone("Asia/Jakarta")

logger = logging.getLogger(__name__)

class TaskHandler:
    def __init__(self, bot):
        self.bot = bot
        self.setup_handlers() 
        logger.info("TaskHandler initialized and handlers set up.")

    def _display_initial_menu(self, notification):
        logger.info(f"_display_initial_menu: Displaying for {notification.sender}")
        notification.answer(
            "*Hi, Skremates!* 💸\n\n"
            "Selamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\n"
            "Apa yang ingin kamu akses?\n\n"
            "1. Lihat Tugas\n"
            "2. Panel Ketua Kelas\n\n"
            "Ketik angka pilihan kamu *(1-2)*"
        )
        notification.state_manager.update_state_data(notification.sender, {"state_history": []}) 
        notification.state_manager.update_state(notification.sender, States.INITIAL)

    def _display_class_selection_menu(self, notification, prefix_message=""):
        logger.info(f"_display_class_selection_menu: Called for {notification.sender}")
        # ... (Implementasi _display_class_selection_menu sama seperti versi lengkap terakhir) ...
        try:
            response = supabase.table('classes').select('id, name').order('id').execute()
            if hasattr(response, 'error') and response.error:
                logger.error(f"_display_class_selection_menu: Supabase error: {response.error}")
                notification.answer(prefix_message + "Gagal mengambil daftar kelas.")
                return False
            classes_data = response.data
            if not classes_data:
                logger.warning("_display_class_selection_menu: No classes found.")
                notification.answer(prefix_message + "Belum ada kelas tersedia.")
                return False
            class_list_str = "\n".join([f"{item['id']}. {item['name']}" for item in classes_data])
            message = (prefix_message + "🧑‍🏫 *Pilih Kelasmu:* 👩‍🏫\n\n" + class_list_str +
                       "\n\n_Note:_\nKetik angka pilihan.\nKetik 0 untuk ke Menu Utama.")
            notification.answer(message)
            return True
        except Exception as e:
            logger.error(f"_display_class_selection_menu: Exception: {e}", exc_info=True)
            notification.answer(prefix_message + "Error menampilkan pilihan kelas.")
            return False


    def _display_day_selection_menu(self, notification, prefix_message=""):
        logger.info(f"_display_day_selection_menu: Called for {notification.sender}")
        # ... (Implementasi _display_day_selection_menu sama seperti versi lengkap terakhir) ...
        try:
            days_response = supabase.table('days').select('id, name').order('id').execute()
            if hasattr(days_response, 'error') and days_response.error:
                logger.error(f"_display_day_selection_menu: Supabase error: {days_response.error}")
                notification.answer(prefix_message + "Gagal mengambil daftar hari.")
                return False
            days_data = days_response.data
            if not days_data:
                logger.warning("_display_day_selection_menu: No days found.")
                notification.answer(prefix_message + "Belum ada hari tersedia.")
                return False
            day_list_str = "\n".join([f"{item['id']}. {item['name']}" for item in days_data])
            message = (prefix_message + "🗓️ *Pilih Hari Pengumpulan:* 🗓️\n\n" + day_list_str +
                       "\n\n_Note:_\nKetik angka pilihan.\nKetik 0 untuk ke Pilihan Kelas.")
            notification.answer(message)
            return True
        except Exception as e:
            logger.error(f"_display_day_selection_menu: Exception: {e}", exc_info=True)
            notification.answer(prefix_message + "Error menampilkan pilihan hari.")
            return False

    def _display_task_list_menu(self, notification, tasks_data, day_name, prefix_message=""):
        logger.info(f"_display_task_list_menu: Called for {notification.sender} for day {day_name}")
        # ... (Implementasi _display_task_list_menu sama seperti versi lengkap terakhir) ...
        tasks_list_display = []
        for idx, task in enumerate(tasks_data, 1):
            task_name = task.get('name', 'N/A')
            task_description = task.get('description', 'N/A')
            task_due_iso = task.get('due_date')
            due_date_display = "N/A"
            if task_due_iso:
                due_date_utc = datetime.fromisoformat(task_due_iso.replace('Z', '+00:00'))
                due_date_wib = due_date_utc.astimezone(indonesia_tz)
                due_date_display = due_date_wib.strftime('%d/%m/%Y %H:%M WIB')
            tasks_list_display.append(f"{idx}. {task_name}\n🗒️ {task_description}\n⏰ {due_date_display}")
        
        message = (prefix_message + f"📚 *Tugas untuk hari {day_name}*:\n\n" +
                   "\n\n".join(tasks_list_display) +
                   "\n\n_Note:_\nKetik angka tugas untuk detail & reminder.\nKetik 0 untuk kembali ke Pilihan Hari.")    
        notification.answer(message)


    def _display_task_detail_menu(self, notification, task_data, prefix_message=""):
        logger.info(f"_display_task_detail_menu: Displaying detail for task: {task_data.get('name')}")
        # ... (Implementasi _display_task_detail_menu sama seperti versi lengkap terakhir) ...
        task_name = task_data.get('name', 'N/A')
        task_description = task_data.get('description', 'N/A')
        task_due_iso = task_data.get('due_date')
        task_type = task_data.get('jenis_tugas', 'N/A').capitalize()
        due_date_display = "N/A"
        if task_due_iso:
            due_date_utc = datetime.fromisoformat(task_due_iso.replace('Z', '+00:00'))
            due_date_wib = due_date_utc.astimezone(indonesia_tz)
            due_date_display = due_date_wib.strftime('%d/%m/%Y %H:%M WIB')
        
        message = (
            prefix_message + f"📚 *Detail Tugas:*\n\n"
            f"📝 *Nama:* {task_name}\n📖 *Deskripsi:* {task_description}\n"
            f"⏰ *Deadline:* {due_date_display}\n📂 *Jenis:* {task_type}\n\n"
            "Apakah ingin diingatkan untuk tugas ini?\n1. ✅ Ya\n2. ❌ Tidak\n0. Kembali ke Daftar Tugas."
        )
        notification.answer(message)

    def setup_handlers(self):
        logger.info("TaskHandler: Setting up message handlers.")

        @self.bot.router.message(type_message="textMessage", state=States.CLASS_SELECTION)
        def class_selection_state_handler(notification):
            logger.info(f"CLASS_SELECTION_STATE_HANDLER: Received '{notification.message_text}' from {notification.sender}")
            if notification.message_text == "0":
                self._display_initial_menu(notification)
            elif notification.message_text.isdigit() and 1 <= int(notification.message_text) <= 8: 
                self.class_selection_handler(notification)
            else:
                self.show_invalid_message(notification, States.CLASS_SELECTION)

        @self.bot.router.message(type_message="textMessage", state=States.DAY_SELECTION)
        def day_selection_state_handler(notification):
            logger.info(f"DAY_SELECTION_STATE_HANDLER: Received '{notification.message_text}' from {notification.sender}")
            if notification.message_text == "0":
                self.start_flow_handler(notification) 
            elif notification.message_text.isdigit() and 1 <= int(notification.message_text) <= 7: 
                self.day_selection_handler(notification)
            else:
                self.show_invalid_message(notification, States.DAY_SELECTION)

        @self.bot.router.message(type_message="textMessage", state=States.TASK_LIST)
        def task_list_state_handler(notification):
            logger.info(f"TASK_LIST_STATE_HANDLER: Received '{notification.message_text}' from {notification.sender}")
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            if notification.message_text == "0":
                selected_class_id = state_data.get("selected_class_id")
                if selected_class_id:
                    temp_notif = type('TempNotif', (), {'sender': notification.sender, 'message_text': selected_class_id, 'state_manager': notification.state_manager})()
                    self.class_selection_handler(temp_notif) 
                else: 
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
                selected_day_id = state_data.get("selected_day_id")
                selected_class_id = state_data.get("selected_class_id") 
                if selected_day_id and selected_class_id:
                    temp_notif = type('TempNotif', (), {'sender': notification.sender, 'message_text': selected_day_id, 'state_manager': notification.state_manager})()
                    # Pastikan selected_class_id ada di state sebelum panggil day_selection_handler
                    # Ini penting karena day_selection_handler mengambil selected_class_id dari state
                    notification.state_manager.update_state_data(notification.sender, {"selected_class_id": selected_class_id, "state_history": state_data.get("state_history", [])})
                    self.day_selection_handler(temp_notif)
                else: 
                    self.start_flow_handler(notification)
            elif notification.message_text == "1": 
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
                    
                    records_to_insert = []
                    reminder_types_map = ["H-3D", "H-1D", "H-1H"] 
                    
                    for i, time_iso_str in enumerate(notify_times_utc_iso):
                        records_to_insert.append({
                            "phone_number": notification.sender, "task_id": task['id'],
                            "notification_time": time_iso_str, # Kolom BARU: timestamp tunggal
                            "reminder_type": reminder_types_map[i], # Kolom BARU: tipe reminder
                            "is_sent": False
                        })
                    
                    if records_to_insert:
                        logger.info(f"Attempting to insert {len(records_to_insert)} notification records.")
                        response = supabase.table('notifications').insert(records_to_insert).execute()
                        
                        if hasattr(response, 'error') and response.error:
                            logger.error(f"Supabase error saving notifications: {response.error}")
                            notification.answer(f"❌ *Gagal menyimpan notifikasi ke DB*\nError: {response.error.message if hasattr(response.error, 'message') else response.error}")
                        elif response.data:
                            logger.info(f"Reminders successfully set for task ID {task['id']}.")
                            notification.answer(f"✅ *Reminder berhasil diatur!*\n\nKamu akan menerima reminder untuk tugas:\n📝 {task.get('name', 'N/A')}\n\nReminder akan dikirim pada jadwalnya.")
                            self._display_initial_menu(notification)
                        else:
                            logger.warning(f"Failed to save notifications, no data/error in response: {response}")
                            notification.answer("❌ *Gagal menyimpan notifikasi (DB issue)*\nSilakan coba lagi.")
                    else: # Seharusnya tidak terjadi jika calculate_notification_times benar
                        logger.error("No notification records generated to insert.")
                        notification.answer("❌ *Gagal mengatur reminder: Tidak ada waktu notifikasi dihasilkan*")
                except Exception as e:
                    logger.error(f"Python exception saving notifications: {e}", exc_info=True)
                    notification.answer("❌ *Terjadi kesalahan sistem saat mengatur reminder.*")
            elif notification.message_text == "2": 
                self.skip_reminder_handler(notification)
            else:
                self.show_invalid_message(notification, States.NOTIFICATION_SETUP)

    def start_flow_handler(self, notification):
        logger.info(f"START_FLOW_HANDLER: Called by {notification.sender}")
        current_state_data = notification.state_manager.get_state_data(notification.sender) or {}
        history = current_state_data.get("state_history", [])
        clean_flow_state = {"state_history": history, "selected_class_id": None, "selected_day_id": None, "tasks": None, "selected_task": None} 
        notification.state_manager.update_state_data(notification.sender, clean_flow_state)
        logger.info(f"START_FLOW_HANDLER: Task flow state cleared for {notification.sender}, preserving history.")
        if self._display_class_selection_menu(notification):
            update_state_with_history(notification, States.CLASS_SELECTION)

    def class_selection_handler(self, notification):
        selected_class_id_str = notification.message_text
        logger.info(f"CLASS_SELECTION_HANDLER: User {notification.sender} selected class ID '{selected_class_id_str}'")
        current_state_data = notification.state_manager.get_state_data(notification.sender) or {}
        history = current_state_data.get("state_history", [])
        updated_flow_data = {
            "selected_class_id": selected_class_id_str, "state_history": history,
            "selected_day_id": None, "tasks": None, "selected_task": None 
        }
        notification.state_manager.update_state_data(notification.sender, updated_flow_data)
        logger.info(f"CLASS_SELECTION_HANDLER: State updated for {notification.sender}. selected_class_id: '{selected_class_id_str}'. Other task states reset.")
        if self._display_day_selection_menu(notification):
            update_state_with_history(notification, States.DAY_SELECTION)

    def day_selection_handler(self, notification):
        selected_day_id_str = notification.message_text 
        logger.info(f"DAY_SELECTION_HANDLER: User {notification.sender} selected day ID '{selected_day_id_str}'")
        try:
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            selected_class_id_str = state_data.get("selected_class_id")
            if not selected_class_id_str:
                logger.error(f"DAY_SELECTION_HANDLER: selected_class_id NOT FOUND for {notification.sender}.")
                notification.answer("Kesalahan: Kelas belum dipilih. Ulangi.")
                self.start_flow_handler(notification)
                return
            try:
                class_id_for_query = int(selected_class_id_str)
                day_id_for_query = int(selected_day_id_str) 
            except ValueError:
                logger.error(f"DAY_SELECTION_HANDLER: Invalid ID format. Class: '{selected_class_id_str}', Day: '{selected_day_id_str}'")
                notification.answer("Format ID tidak valid. Ulangi.")
                self.start_flow_handler(notification)
                return
            
            logger.info(f"DAY_SELECTION_HANDLER: Querying tasks for class_id: {class_id_for_query}, day_id: {day_id_for_query}")
            day_name_response = supabase.table('days').select('name').eq('id', day_id_for_query).maybe_single().execute()
            day_name = day_name_response.data['name'] if day_name_response.data else f"ID Hari {day_id_for_query}"

            tasks_response = supabase.table('tasks') \
                .select('id, name, description, due_date, jenis_tugas, class_id, day_id') \
                .eq('class_id', class_id_for_query) \
                .eq('day_id', day_id_for_query) \
                .order('due_date').execute()
            if hasattr(tasks_response, 'error') and tasks_response.error:
                logger.error(f"DAY_SELECTION_HANDLER: Supabase error: {tasks_response.error}")
                notification.answer("Error mengambil daftar tugas.")
                return

            tasks_data = tasks_response.data
            logger.info(f"DAY_SELECTION_HANDLER: Found {len(tasks_data)} tasks for class {class_id_for_query} day {day_id_for_query}. Data: {tasks_data if tasks_data else '[]'}")

            if not tasks_data: # BUG 2 - Perbaikan logika kembali
                notification.answer(f"📭 Yeay! Tidak ada tugas untuk kelas yang dipilih pada hari {day_name}.")
                logger.info(f"DAY_SELECTION_HANDLER: No tasks for class {selected_class_id_str}, day {day_name}. Displaying day selection menu again.")
                # Pertahankan selected_class_id, reset state lain, dan tampilkan menu hari lagi
                current_history = state_data.get("state_history", [])
                notification.state_manager.update_state_data(notification.sender, {
                    "selected_class_id": selected_class_id_str, 
                    "state_history": current_history,
                    "selected_day_id": None, "tasks": None, "selected_task": None
                })
                if self._display_day_selection_menu(notification): # Menampilkan menu pilih hari untuk kelas yang sama
                     update_state_with_history(notification, States.DAY_SELECTION) # Kembali ke state pilih hari
                else: # Fallback jika gagal tampilkan menu
                    self.start_flow_handler(notification)
                return
            
            history = state_data.get("state_history", [])
            notification.state_manager.update_state_data(
                notification.sender, {
                    "tasks": tasks_data, "selected_day_id": selected_day_id_str,
                    "selected_class_id": selected_class_id_str, "state_history": history,
                    "selected_task": None 
                })
            logger.info(f"DAY_SELECTION_HANDLER: State updated with {len(tasks_data)} tasks for {notification.sender}.")
            self._display_task_list_menu(notification, tasks_data, day_name)
            update_state_with_history(notification, States.TASK_LIST)
        except Exception as e:
            logger.error(f"DAY_SELECTION_HANDLER: Exception: {e}", exc_info=True)
            notification.answer("Error sistem memproses pilihan hari.")

    def task_detail_handler(self, notification):
        # ... (Implementasi sama seperti sebelumnya, pastikan pengecekan `task_idx_chosen` dan `due_date` ada) ...
        selected_task_index_str = notification.message_text
        logger.info(f"TASK_DETAIL_HANDLER: User {notification.sender} selected index str '{selected_task_index_str}'")
        try:
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            tasks_in_state = state_data.get("tasks", [])
            if not selected_task_index_str.isdigit(): 
                self.show_invalid_message(notification, States.TASK_LIST); return
            task_idx_chosen = int(selected_task_index_str) - 1
            if not (0 <= task_idx_chosen < len(tasks_in_state)):
                self.show_invalid_message(notification, States.TASK_LIST); return
            selected_task_data = tasks_in_state[task_idx_chosen]
            if not selected_task_data.get('due_date'): 
                logger.error(f"Task {selected_task_data.get('id')} missing due_date.")
                notification.answer("Detail tugas tidak lengkap (tidak ada deadline).")
                # Panggil helper untuk menampilkan list lagi, butuh day_name
                day_id_for_name = state_data.get("selected_day_id")
                day_name_for_list = "hari terpilih"
                if day_id_for_name:
                    day_name_resp = supabase.table('days').select('name').eq('id', int(day_id_for_name)).maybe_single().execute()
                    if day_name_resp.data: day_name_for_list = day_name_resp.data['name']
                self._display_task_list_menu(notification, tasks_in_state, day_name_for_list) 
                return

            self._display_task_detail_menu(notification, selected_task_data)
            history = state_data.get("state_history", [])
            notification.state_manager.update_state_data(
                notification.sender, {
                    "selected_task": selected_task_data, "tasks": tasks_in_state, 
                    "selected_day_id": state_data.get("selected_day_id"), 
                    "selected_class_id": state_data.get("selected_class_id"), 
                    "state_history": history
                })
            update_state_with_history(notification, States.NOTIFICATION_SETUP)
        except Exception as e:
            logger.error(f"TASK_DETAIL_HANDLER: Exception: {e}", exc_info=True)
            notification.answer("Error sistem menampilkan detail tugas.")


    def skip_reminder_handler(self, notification):
        logger.info(f"SKIP_REMINDER_HANDLER: User {notification.sender} chose not to set reminder.")
        notification.answer("ℹ️ Tidak ada reminder yang diatur untuk tugas ini.")
        self._display_initial_menu(notification)

    def show_invalid_message(self, notification, current_state: str):
        # ... (Implementasi show_invalid_message sama seperti versi lengkap terakhir) ...
        logger.warning(f"SHOW_INVALID_MESSAGE: Invalid input by {notification.sender} in state {current_state}. Text: '{notification.message_text}'")
        prefix = "⚠️ *Input tidak valid!*\n\n"
        if current_state == States.CLASS_SELECTION:
            self._display_class_selection_menu(notification, prefix_message=prefix)
        elif current_state == States.DAY_SELECTION:
            self._display_day_selection_menu(notification, prefix_message=prefix)
        elif current_state == States.TASK_LIST:
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            tasks = state_data.get("tasks", [])
            day_id = state_data.get("selected_day_id")
            day_name = "hari terpilih"
            if day_id:
                day_resp = supabase.table('days').select('name').eq('id', int(day_id)).maybe_single().execute()
                if day_resp.data: day_name = day_resp.data['name']
            if tasks: self._display_task_list_menu(notification, tasks, day_name, prefix_message=prefix)
            else: notification.answer(prefix + "Tidak ada daftar tugas untuk ditampilkan."); self._display_day_selection_menu(notification)
        elif current_state == States.NOTIFICATION_SETUP:
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            task = state_data.get("selected_task")
            if task: self._display_task_detail_menu(notification, task, prefix_message=prefix)
            else: 
                notification.answer(prefix + "Detail tugas tidak ditemukan.")
                # Arahkan kembali ke daftar tugas jika memungkinkan
                day_id_for_r = state_data.get("selected_day_id")
                if day_id_for_r:
                    temp_notif_r = type('TempNotif', (), {'sender': notification.sender, 'message_text': day_id_for_r, 'state_manager': notification.state_manager})()
                    self.day_selection_handler(temp_notif_r)
                else:
                    self._display_initial_menu(notification)
        else: 
             self._display_initial_menu(notification)