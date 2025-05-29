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
        state_data = notification.state_manager.get_state_data(notification.sender) or {}
        selected_class_id_str = state_data.get("selected_class_id")

        if not selected_class_id_str:
            logger.error(f"_display_day_selection_menu: selected_class_id not found in state for {notification.sender}")
            notification.answer(prefix_message + "Kesalahan: Kelas belum dipilih. Silakan mulai dari awal dengan memilih kelas terlebih dahulu.")
            # Kembali ke menu awal atau pemilihan kelas jika ID kelas tidak ada
            # self.start_flow_handler(notification) # atau
            self._display_initial_menu(notification)
            return False

        try:
            selected_class_id = int(selected_class_id_str)
        except ValueError:
            logger.error(f"_display_day_selection_menu: Invalid selected_class_id format '{selected_class_id_str}' for {notification.sender}")
            notification.answer(prefix_message + "Kesalahan: Format ID kelas tidak valid. Silakan mulai dari awal.")
            self._display_initial_menu(notification)
            return False

        try:
            days_response = supabase.table('days').select('id, name').order('id').execute()
            if hasattr(days_response, 'error') and days_response.error:
                logger.error(f"_display_day_selection_menu: Supabase error fetching days: {days_response.error}")
                notification.answer(prefix_message + "Gagal mengambil daftar hari.")
                return False
            days_data = days_response.data
            if not days_data:
                logger.warning("_display_day_selection_menu: No days found in 'days' table.")
                notification.answer(prefix_message + "Belum ada hari tersedia.")
                return False

            day_details_list = []
            for day_item in days_data:
                day_id = day_item['id']
                day_name = day_item['name']

                # Fetch tasks for this day_id and selected_class_id
                tasks_for_day_response = supabase.table('tasks') \
                    .select('name') \
                    .eq('class_id', selected_class_id) \
                    .eq('day_id', day_id) \
                    .execute()

                if hasattr(tasks_for_day_response, 'error') and tasks_for_day_response.error:
                    logger.error(f"_display_day_selection_menu: Supabase error fetching tasks for day_id {day_id}, class_id {selected_class_id}: {tasks_for_day_response.error}")
                    # Menampilkan error untuk hari spesifik ini, namun menu tetap lanjut
                    day_details_list.append(f"{day_id}. {day_name}: (Error mengambil data tugas)")
                    continue

                day_tasks_data = tasks_for_day_response.data
                task_count = len(day_tasks_data)

                if task_count > 0:
                    task_names = [task['name'] for task in day_tasks_data]
                    # Batasi jumlah nama tugas yang ditampilkan jika terlalu banyak, misal 3 nama pertama
                    max_names_to_show = 3
                    if len(task_names) > max_names_to_show:
                        task_names_display = ", ".join(task_names[:max_names_to_show]) + ", ..."
                    else:
                        task_names_display = ", ".join(task_names)
                    day_details_list.append(f"{day_id}. {day_name}: {task_count} ({task_names_display})")
                else:
                    day_details_list.append(f"{day_id}. {day_name}: 0")

            day_list_str = "\n".join(day_details_list)
            message = (prefix_message + "🗓️ *Pilih Hari Pengumpulan:* 🗓️\n\n" + day_list_str +
                       "\n\n_Note:_\nKetik angka pilihan.\nKetik 0 untuk ke Pilihan Kelas.")
            notification.answer(message)
            return True
        except Exception as e:
            logger.error(f"_display_day_selection_menu: Exception: {e}", exc_info=True)
            notification.answer(prefix_message + "Error menampilkan pilihan hari dengan detail tugas.")
            return False

    def _display_task_list_menu(self, notification, tasks_data, day_name, prefix_message=""):
        logger.info(f"_display_task_list_menu: Called for {notification.sender} for day {day_name}")
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
            elif notification.message_text.isdigit() and 1 <= int(notification.message_text) <= 3: # Asumsi maks 8 kelas, sesuaikan jika perlu
                self.class_selection_handler(notification)
            else:
                self.show_invalid_message(notification, States.CLASS_SELECTION)

        @self.bot.router.message(type_message="textMessage", state=States.DAY_SELECTION)
        def day_selection_state_handler(notification):
            logger.info(f"DAY_SELECTION_STATE_HANDLER: Received '{notification.message_text}' from {notification.sender}")
            if notification.message_text == "0":
                # Kembali ke pemilihan kelas
                self.start_flow_handler(notification) # Ini akan menampilkan menu pemilihan kelas
            elif notification.message_text.isdigit() and 1 <= int(notification.message_text) <= 7: # Asumsi 7 hari
                self.day_selection_handler(notification)
            else:
                self.show_invalid_message(notification, States.DAY_SELECTION)

        @self.bot.router.message(type_message="textMessage", state=States.TASK_LIST)
        def task_list_state_handler(notification):
            logger.info(f"TASK_LIST_STATE_HANDLER: Received '{notification.message_text}' from {notification.sender}")
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            if notification.message_text == "0":
                # Kembali ke pemilihan hari
                selected_class_id = state_data.get("selected_class_id")
                if selected_class_id:
                    # Buat notifikasi sementara untuk memicu _display_day_selection_menu
                    # Pastikan state 'selected_class_id' sudah ada
                    notification.state_manager.update_state_data(notification.sender, {
                        "selected_class_id": selected_class_id,
                        "state_history": state_data.get("state_history", []),
                        "selected_day_id": None, "tasks": None, "selected_task": None
                    })
                    if self._display_day_selection_menu(notification):
                        update_state_with_history(notification, States.DAY_SELECTION)
                    else: # Fallback jika _display_day_selection_menu gagal
                        self.start_flow_handler(notification)
                else:
                    self.start_flow_handler(notification) # Fallback jika class_id tidak ada
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
                # Kembali ke daftar tugas
                selected_day_id = state_data.get("selected_day_id")
                selected_class_id = state_data.get("selected_class_id")
                tasks_in_state = state_data.get("tasks") # Ambil tasks dari state
                day_name = "hari terpilih" # Default
                
                if selected_day_id: # coba dapatkan nama hari jika ada day_id
                    day_name_resp = supabase.table('days').select('name').eq('id', int(selected_day_id)).maybe_single().execute()
                    if day_name_resp.data: day_name = day_name_resp.data['name']

                if tasks_in_state and selected_day_id and selected_class_id:
                     notification.state_manager.update_state_data(
                        notification.sender, {
                            "tasks": tasks_in_state, "selected_day_id": selected_day_id,
                            "selected_class_id": selected_class_id, "state_history": state_data.get("state_history",[]),
                            "selected_task": None # Reset selected_task
                        })
                     self._display_task_list_menu(notification, tasks_in_state, day_name)
                     update_state_with_history(notification, States.TASK_LIST)
                else:
                    # Fallback jika data tidak lengkap untuk kembali ke list tugas
                    logger.warning("NOTIFICATION_SETUP_HANDLER: Data incomplete to go back to task list. Going to day selection.")
                    if selected_class_id:
                        notification.state_manager.update_state_data(notification.sender, {
                            "selected_class_id": selected_class_id, 
                            "state_history": state_data.get("state_history", []),
                            "selected_day_id": None, "tasks": None, "selected_task": None
                        })
                        if self._display_day_selection_menu(notification):
                             update_state_with_history(notification, States.DAY_SELECTION)
                        else: self.start_flow_handler(notification)
                    else: self.start_flow_handler(notification)

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
                    reminder_types_map = ["H-3D", "H-1D", "H-1H"] # Sesuai dengan output calculate_notification_times

                    for i, time_iso_str in enumerate(notify_times_utc_iso):
                        records_to_insert.append({
                            "phone_number": notification.sender, "task_id": task['id'],
                            "notification_time": time_iso_str,
                            "reminder_type": reminder_types_map[i],
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
                            self._display_initial_menu(notification) # Kembali ke menu awal setelah sukses
                        else:
                            logger.warning(f"Failed to save notifications, no data/error in response: {response}")
                            notification.answer("❌ *Gagal menyimpan notifikasi (DB issue)*\nSilakan coba lagi.")
                    else:
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
        # Hanya reset state yang berkaitan dengan alur tugas, pertahankan history
        clean_flow_state = {
            "state_history": history,
            "selected_class_id": None,
            "selected_day_id": None,
            "tasks": None,
            "selected_task": None
        }
        notification.state_manager.update_state_data(notification.sender, clean_flow_state)
        logger.info(f"START_FLOW_HANDLER: Task flow state cleared for {notification.sender}, preserving history if any.")
        if self._display_class_selection_menu(notification):
            update_state_with_history(notification, States.CLASS_SELECTION)

    def class_selection_handler(self, notification):
        selected_class_id_str = notification.message_text
        logger.info(f"CLASS_SELECTION_HANDLER: User {notification.sender} selected class ID '{selected_class_id_str}'")
        current_state_data = notification.state_manager.get_state_data(notification.sender) or {}
        history = current_state_data.get("state_history", [])
        # Update state dengan class_id yang baru dipilih, reset state berikutnya dalam alur
        updated_flow_data = {
            "selected_class_id": selected_class_id_str,
            "state_history": history,
            "selected_day_id": None, # Reset pilihan hari
            "tasks": None,           # Reset daftar tugas
            "selected_task": None    # Reset tugas terpilih
        }
        notification.state_manager.update_state_data(notification.sender, updated_flow_data)
        logger.info(f"CLASS_SELECTION_HANDLER: State updated for {notification.sender}. selected_class_id: '{selected_class_id_str}'. Subsequent task states reset.")
        if self._display_day_selection_menu(notification): # Tampilkan menu pemilihan hari setelah kelas dipilih
            update_state_with_history(notification, States.DAY_SELECTION)


    def day_selection_handler(self, notification):
        selected_day_id_str = notification.message_text
        logger.info(f"DAY_SELECTION_HANDLER: User {notification.sender} selected day ID '{selected_day_id_str}'")
        try:
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            selected_class_id_str = state_data.get("selected_class_id")
            if not selected_class_id_str:
                logger.error(f"DAY_SELECTION_HANDLER: selected_class_id NOT FOUND for {notification.sender}. Redirecting to start.")
                notification.answer("Kesalahan: Kelas belum dipilih. Mohon ulangi dari awal.")
                self.start_flow_handler(notification)
                return

            try:
                class_id_for_query = int(selected_class_id_str)
                day_id_for_query = int(selected_day_id_str)
            except ValueError:
                logger.error(f"DAY_SELECTION_HANDLER: Invalid ID format. Class: '{selected_class_id_str}', Day: '{selected_day_id_str}'. Redirecting.")
                notification.answer("Format ID tidak valid. Mohon ulangi.")
                # Mungkin kembali ke pemilihan kelas atau hari, tergantung logika yg diinginkan
                self.start_flow_handler(notification) # Kembali ke awal untuk memilih kelas lagi
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
                logger.error(f"DAY_SELECTION_HANDLER: Supabase error fetching tasks: {tasks_response.error}")
                notification.answer("Error mengambil daftar tugas dari database.")
                # Pertimbangkan untuk kembali ke menu pemilihan hari atau kelas
                if self._display_day_selection_menu(notification): # Coba tampilkan menu hari lagi
                     update_state_with_history(notification, States.DAY_SELECTION)
                else: # Fallback
                    self.start_flow_handler(notification)
                return

            tasks_data = tasks_response.data
            logger.info(f"DAY_SELECTION_HANDLER: Found {len(tasks_data)} tasks for class {class_id_for_query} day {day_id_for_query}.")

            if not tasks_data:
                notification.answer(f"📭 Yeay! Tidak ada tugas untuk kelas yang dipilih pada hari {day_name}.")
                logger.info(f"DAY_SELECTION_HANDLER: No tasks for class {selected_class_id_str}, day {day_name}. Displaying day selection menu again.")
                # State untuk selected_class_id dan history dipertahankan, reset lainnya
                current_history = state_data.get("state_history", [])
                notification.state_manager.update_state_data(notification.sender, {
                    "selected_class_id": selected_class_id_str,
                    "state_history": current_history,
                    "selected_day_id": None, # Reset pilihan hari
                    "tasks": None,           # Reset daftar tugas
                    "selected_task": None    # Reset tugas terpilih
                })
                if self._display_day_selection_menu(notification): # Tampilkan kembali menu pilih hari
                     update_state_with_history(notification, States.DAY_SELECTION)
                else: # Fallback jika gagal
                    self.start_flow_handler(notification)
                return

            history = state_data.get("state_history", [])
            notification.state_manager.update_state_data(
                notification.sender, {
                    "tasks": tasks_data,
                    "selected_day_id": selected_day_id_str, # Simpan hari yang dipilih
                    "selected_class_id": selected_class_id_str, # Pastikan class_id tetap ada
                    "state_history": history,
                    "selected_task": None # Reset selected_task karena baru memilih hari
                })
            logger.info(f"DAY_SELECTION_HANDLER: State updated with {len(tasks_data)} tasks for {notification.sender}.")
            self._display_task_list_menu(notification, tasks_data, day_name)
            update_state_with_history(notification, States.TASK_LIST)

        except Exception as e:
            logger.error(f"DAY_SELECTION_HANDLER: Exception: {e}", exc_info=True)
            notification.answer("Terjadi error sistem saat memproses pilihan hari Anda.")
            # Pertimbangkan fallback yang lebih aman, misal kembali ke menu awal
            self.start_flow_handler(notification)

    def task_detail_handler(self, notification):
        selected_task_index_str = notification.message_text
        logger.info(f"TASK_DETAIL_HANDLER: User {notification.sender} selected task index str '{selected_task_index_str}'")
        try:
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            tasks_in_state = state_data.get("tasks", [])

            if not selected_task_index_str.isdigit():
                logger.warning(f"TASK_DETAIL_HANDLER: Non-digit input '{selected_task_index_str}'")
                self.show_invalid_message(notification, States.TASK_LIST)
                return

            task_idx_chosen = int(selected_task_index_str) - 1

            if not (0 <= task_idx_chosen < len(tasks_in_state)):
                logger.warning(f"TASK_DETAIL_HANDLER: Index {task_idx_chosen} out of bounds for {len(tasks_in_state)} tasks.")
                self.show_invalid_message(notification, States.TASK_LIST)
                return

            selected_task_data = tasks_in_state[task_idx_chosen]

            if not selected_task_data.get('due_date'):
                logger.error(f"Task {selected_task_data.get('id', 'N/A')} (index {task_idx_chosen}) is missing 'due_date'. Task data: {selected_task_data}")
                notification.answer("❌ Detail tugas ini tidak lengkap (tidak ada tanggal deadline). Tidak dapat menampilkan detail.")
                # Kembali ke daftar tugas
                day_id_for_name = state_data.get("selected_day_id")
                day_name_for_list = "hari terpilih"
                if day_id_for_name:
                    day_name_resp = supabase.table('days').select('name').eq('id', int(day_id_for_name)).maybe_single().execute()
                    if day_name_resp.data: day_name_for_list = day_name_resp.data['name']
                self._display_task_list_menu(notification, tasks_in_state, day_name_for_list)
                # State tetap TASK_LIST karena hanya menampilkan ulang menu
                # update_state_with_history(notification, States.TASK_LIST) # Tidak perlu update state karena sudah di TASK_LIST
                return

            self._display_task_detail_menu(notification, selected_task_data)
            # Update state dengan task yang dipilih
            history = state_data.get("state_history", [])
            notification.state_manager.update_state_data(
                notification.sender, {
                    "selected_task": selected_task_data,
                    "tasks": tasks_in_state, # Pertahankan daftar tugas
                    "selected_day_id": state_data.get("selected_day_id"), # Pertahankan hari
                    "selected_class_id": state_data.get("selected_class_id"), # Pertahankan kelas
                    "state_history": history
                })
            update_state_with_history(notification, States.NOTIFICATION_SETUP)
        except Exception as e:
            logger.error(f"TASK_DETAIL_HANDLER: Exception: {e}", exc_info=True)
            notification.answer("Terjadi error sistem saat menampilkan detail tugas.")
            # Pertimbangkan fallback, misal kembali ke daftar tugas atau menu hari
            # self.day_selection_handler(notification) # atau state sebelumnya


    def skip_reminder_handler(self, notification):
        logger.info(f"SKIP_REMINDER_HANDLER: User {notification.sender} chose not to set reminder.")
        notification.answer("ℹ️ Tidak ada reminder yang diatur untuk tugas ini.")
        self._display_initial_menu(notification) # Kembali ke menu awal


    def show_invalid_message(self, notification, current_state: str):
        logger.warning(f"SHOW_INVALID_MESSAGE: Invalid input by {notification.sender} in state {current_state}. Text: '{notification.message_text}'")
        prefix = "⚠️ *Input tidak valid!*\n\n"
        state_data = notification.state_manager.get_state_data(notification.sender) or {}

        if current_state == States.CLASS_SELECTION:
            self._display_class_selection_menu(notification, prefix_message=prefix)
        elif current_state == States.DAY_SELECTION:
            # Memastikan selected_class_id ada sebelum memanggil _display_day_selection_menu
            if state_data.get("selected_class_id"):
                self._display_day_selection_menu(notification, prefix_message=prefix)
            else:
                logger.error("SHOW_INVALID_MESSAGE: Cannot display day selection, class_id missing. Going to initial menu.")
                notification.answer(prefix + "Pilihan kelas tidak ditemukan. Silakan mulai dari awal.")
                self._display_initial_menu(notification)
        elif current_state == States.TASK_LIST:
            tasks = state_data.get("tasks", [])
            day_id = state_data.get("selected_day_id")
            day_name = "hari terpilih"
            if day_id:
                try:
                    day_resp = supabase.table('days').select('name').eq('id', int(day_id)).maybe_single().execute()
                    if day_resp.data: day_name = day_resp.data['name']
                except ValueError: # Jika day_id tidak bisa di-cast ke int
                     logger.error(f"SHOW_INVALID_MESSAGE: Invalid day_id '{day_id}' in state for TASK_LIST.")

            if tasks:
                self._display_task_list_menu(notification, tasks, day_name, prefix_message=prefix)
            else:
                # Jika tidak ada tasks, coba kembali ke menu pemilihan hari
                logger.warning("SHOW_INVALID_MESSAGE: No tasks in state for TASK_LIST. Attempting to show day selection.")
                if state_data.get("selected_class_id"):
                    self._display_day_selection_menu(notification, prefix_message=prefix + "Tidak ada daftar tugas untuk ditampilkan. ")
                else:
                    notification.answer(prefix + "Tidak ada daftar tugas dan info kelas tidak ditemukan.")
                    self._display_initial_menu(notification)
        elif current_state == States.NOTIFICATION_SETUP:
            task = state_data.get("selected_task")
            if task:
                self._display_task_detail_menu(notification, task, prefix_message=prefix)
            else:
                # Jika tidak ada task terpilih, coba kembali ke daftar tugas
                logger.warning("SHOW_INVALID_MESSAGE: No selected_task in state for NOTIFICATION_SETUP. Attempting to show task list.")
                tasks_in_state = state_data.get("tasks", [])
                day_id_for_list = state_data.get("selected_day_id")
                day_name_for_list_fallback = "hari terpilih"
                if day_id_for_list:
                    try:
                        day_name_resp_fallback = supabase.table('days').select('name').eq('id', int(day_id_for_list)).maybe_single().execute()
                        if day_name_resp_fallback.data: day_name_for_list_fallback = day_name_resp_fallback.data['name']
                    except ValueError:
                        logger.error(f"SHOW_INVALID_MESSAGE: Invalid day_id '{day_id_for_list}' in state for NOTIFICATION_SETUP fallback.")

                if tasks_in_state:
                    self._display_task_list_menu(notification, tasks_in_state, day_name_for_list_fallback, prefix_message=prefix + "Detail tugas tidak ditemukan. ")
                    update_state_with_history(notification, States.TASK_LIST) # Pastikan state kembali ke TASK_LIST
                else:
                    notification.answer(prefix + "Detail tugas tidak ditemukan dan daftar tugas juga kosong.")
                    self._display_initial_menu(notification) # Fallback ke menu awal jika semua gagal
        else:
             self._display_initial_menu(notification)