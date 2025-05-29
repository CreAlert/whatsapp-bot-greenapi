# admin_handler.py
from datetime import datetime
# from typing import List, Dict # Not directly used in this specific snippet modification
import logging
from ..config import States, supabase, is_admin
from ..utils import update_state_with_history
try:
    from zoneinfo import ZoneInfo
    indonesia_tz = ZoneInfo("Asia/Jakarta")
except ImportError:
    import pytz
    indonesia_tz = pytz.timezone("Asia/Jakarta")

logger = logging.getLogger(__name__)

class AdminHandler:
    def __init__(self, bot):
        self.bot = bot
        self.setup_handlers()

    def setup_handlers(self):
        """Setup all admin-related message handlers"""
        @self.bot.router.message(
            type_message="textMessage",
            state=States.INITIAL,
            regexp=r"^2$"
        )
        # No changes needed for admin_menu_handler, admin_menu_back_handler, 
        # or the initial admin_menu_selection_handler routing to start_add_task_flow.
        # We assume they are correct as per your provided code.
        # ... (admin_menu_handler, admin_menu_back_handler, admin_menu_selection_handler from your code) ...
        def admin_menu_handler(notification):
            """Handle admin menu access"""
            if not is_admin(notification.sender):
                notification.answer(
                    "⛔ *Akses Ditolak*\n\n"
                    "Maaf, kamu tidak memiliki akses ke panel ketua kelas.\n"
                    "Silakan pilih menu lain."
                )
                return
            
            notification.answer(
                "*🛠️ Panel Ketua Kelas*\n\n"
                "1. Tambah Tugas Baru\n"
                "2. Kembali ke Menu Utama\n\n"
                "_Note:_\n"
                "Ketik angka sesuai pilihan\n"
                "Ketik 0 untuk kembali ke Home"
            )
            update_state_with_history(notification, States.ADMIN_MENU)

        @self.bot.router.message(
            type_message="textMessage",
            state=States.ADMIN_MENU,
            regexp=r"^2$"
        )
        def admin_menu_back_handler(notification):
            """Handle back navigation from admin menu"""
            notification.answer(
                "*Hi, Skremates!* 💸\n\n"
                "Selamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\n"
                "Apa yang ingin kamu akses?\n\n"
                "1. Lihat Tugas\n"
                "2. Panel Ketua Kelas\n\n"
                "_Note:_\n"
                "Ketik angka sesuai pilihan\n"
                "Ketik 0 untuk kembali ke Home"
            )
            notification.state_manager.update_state(notification.sender, States.INITIAL)

        @self.bot.router.message(
            type_message="textMessage",
            state=States.ADMIN_MENU,
            regexp=r"^1$"
        )
        def admin_menu_selection_handler(notification):
            """Handle admin menu selections"""
            self.start_add_task_flow(notification)


        @self.bot.router.message(
            type_message="textMessage",
            state=States.ADMIN_CLASS_SELECTION
        )
        def admin_class_selection_handler(notification):
            """Handle class selection in admin flow"""
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            admin_task_in_progress = state_data.get("admin_task_in_progress", {})
            history = state_data.get("state_history", [])

            if notification.message_text == "0":
                # This will take them to ADMIN_MENU. 
                # If they start "Add Task" again, start_add_task_flow will reset admin_task_in_progress.
                notification.answer(
                    "*🛠️ Panel Ketua Kelas*\n\n"
                    "1. Tambah Tugas Baru\n"
                    "2. Kembali ke Menu Utama\n\n"
                    "_Note:_\n"
                    "Ketik angka sesuai pilihan\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                # Preserve current admin_task_in_progress if we are just updating history for back nav
                # But since we go to ADMIN_MENU, it will be reset by start_add_task_flow if "Add new task" is chosen.
                # For consistent back navigation logic that preserves form data, this could be more granular.
                # However, the original global_back_handler sends to ADMIN_MENU from ADMIN_ADD_TASK, implying reset is fine.
                # Let's use update_state_with_history which correctly handles history.
                # The current state data (including potentially incomplete admin_task_in_progress) will be passed.
                update_state_with_history(notification, States.ADMIN_MENU) 
                return

            # Validate input (1-8)
            try:
                class_choice = int(notification.message_text)
                if not (1 <= class_choice <= 8): # Assuming max 8 classes, adjust if necessary
                    raise ValueError("Invalid class choice")
            except ValueError:
                response = supabase.table('classes').select('id, name').order('id').execute()
                classes = {str(item['id']): item['name'] for item in response.data}
                class_list = "\n".join([f"{num}. {name}" for num, name in classes.items()])
                notification.answer(
                    "⚠️ *Input tidak valid!*\n\n"
                    "*🧑‍🏫 Pilih Kelas:*\n\n" +
                    class_list +
                    "\n\n_Note:_\n"
                    "Ketik angka sesuai pilihan\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                return

            admin_task_in_progress["selected_class_id"] = notification.message_text
            notification.state_manager.update_state_data(
                notification.sender,
                {"state_history": history, "admin_task_in_progress": admin_task_in_progress}
            )
            
            days_response = supabase.table('days').select('id, name').order('id').execute()
            days = {str(item['id']): item['name'] for item in days_response.data}
            day_list = "\n".join([f"{num}. {name}" for num, name in days.items()])
            
            notification.answer(
                "*🗓️ Pilih Hari Pengumpulan:*\n\n" +
                day_list +
                "\n\n_Note:_\n"
                "Ketik angka sesuai pilihan\n"
                "Ketik 0 untuk kembali ke Home"
            )
            update_state_with_history(notification, States.ADMIN_DAY_SELECTION)

        @self.bot.router.message(
            type_message="textMessage",
            state=States.ADMIN_DAY_SELECTION
        )
        def admin_day_selection_handler(notification):
            """Handle day selection in admin flow"""
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            admin_task_in_progress = state_data.get("admin_task_in_progress", {})
            history = state_data.get("state_history", [])

            if notification.message_text == "0":
                # Go back to class selection
                response = supabase.table('classes').select('id, name').order('id').execute()
                classes = {str(item['id']): item['name'] for item in response.data}
                class_list = "\n".join([f"{num}. {name}" for num, name in classes.items()])
                notification.answer(
                    "*🧑‍🏫 Pilih Kelas:*\n\n" +
                    class_list +
                    "\n\n_Note:_\n"
                    "Ketik angka sesuai pilihan\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                # admin_task_in_progress["selected_class_id"] should still be there
                notification.state_manager.update_state_data(
                    notification.sender,
                    {"state_history": history, "admin_task_in_progress": admin_task_in_progress}
                )
                update_state_with_history(notification, States.ADMIN_CLASS_SELECTION)
                return

            # Validate input (1-7)
            try:
                day_choice = int(notification.message_text)
                if not (1 <= day_choice <= 7): # Assuming 7 days
                    raise ValueError("Invalid day choice")
            except ValueError:
                days_response = supabase.table('days').select('id, name').order('id').execute()
                days = {str(item['id']): item['name'] for item in days_response.data}
                day_list = "\n".join([f"{num}. {name}" for num, name in days.items()])
                notification.answer(
                    "⚠️ *Input tidak valid!*\n\n"
                    "*🗓️ Pilih Hari Pengumpulan:*\n\n" +
                    day_list +
                    "\n\n_Note:_\n"
                    "Ketik angka sesuai pilihan\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                return

            admin_task_in_progress["selected_day_id"] = notification.message_text
            notification.state_manager.update_state_data(
                notification.sender,
                {"state_history": history, "admin_task_in_progress": admin_task_in_progress}
            )
            
            notification.answer(
                "*📝 Masukkan Nama Tugas:*\n\n"
                "_Note:_\n"
                "Ketik nama tugas\n"
                "Ketik 0 untuk kembali ke Home"
            )
            update_state_with_history(notification, States.ADMIN_TASK_NAME)

        @self.bot.router.message(
            type_message="textMessage",
            state=States.ADMIN_TASK_NAME
        )
        def admin_task_name_handler(notification):
            """Handle task name input in admin flow"""
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            admin_task_in_progress = state_data.get("admin_task_in_progress", {})
            history = state_data.get("state_history", [])

            if notification.message_text == "0":
                days_response = supabase.table('days').select('id, name').order('id').execute()
                days = {str(item['id']): item['name'] for item in days_response.data}
                day_list = "\n".join([f"{num}. {name}" for num, name in days.items()])
                notification.answer(
                    "*🗓️ Pilih Hari Pengumpulan:*\n\n" +
                    day_list +
                    "\n\n_Note:_\n"
                    "Ketik angka sesuai pilihan\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                notification.state_manager.update_state_data(
                    notification.sender,
                    {"state_history": history, "admin_task_in_progress": admin_task_in_progress}
                )
                update_state_with_history(notification, States.ADMIN_DAY_SELECTION)
                return

            if not notification.message_text.strip():
                notification.answer(
                    "⚠️ *Input tidak valid!*\n\n"
                    "*📝 Masukkan Nama Tugas:*\n\n"
                    "_Note:_\n"
                    "Ketik nama tugas\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                return

            admin_task_in_progress["task_name"] = notification.message_text.strip()
            notification.state_manager.update_state_data(
                notification.sender,
                {"state_history": history, "admin_task_in_progress": admin_task_in_progress}
            )
            
            notification.answer(
                "*📂 Pilih Jenis Tugas:*\n\n"
                "1. Mandiri\n"
                "2. Kelompok\n"
                "3. Ujian\n"
                "4. Quiz\n"
                "5. Project\n\n"
                "_Note:_\n"
                "Ketik angka sesuai pilihan\n"
                "Ketik 0 untuk kembali ke Home"
            )
            update_state_with_history(notification, States.ADMIN_TASK_TYPE)

        @self.bot.router.message(
            type_message="textMessage",
            state=States.ADMIN_TASK_TYPE
        )
        def admin_task_type_handler(notification):
            """Handle task type selection in admin flow"""
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            admin_task_in_progress = state_data.get("admin_task_in_progress", {})
            history = state_data.get("state_history", [])

            if notification.message_text == "0":
                notification.answer(
                    "*📝 Masukkan Nama Tugas:*\n\n"
                    "_Note:_\n"
                    "Ketik nama tugas\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                notification.state_manager.update_state_data(
                    notification.sender,
                    {"state_history": history, "admin_task_in_progress": admin_task_in_progress}
                )
                update_state_with_history(notification, States.ADMIN_TASK_NAME)
                return

            task_types = {"1": "mandiri", "2": "kelompok", "3": "ujian", "4": "quiz", "5": "project"}
            if notification.message_text not in task_types:
                notification.answer(
                    "⚠️ *Input tidak valid!*\n\n"
                    "*📂 Pilih Jenis Tugas:*\n\n"
                    "1. Mandiri\n"
                    "2. Kelompok\n"
                    "3. Ujian\n"
                    "4. Quiz\n"
                    "5. Project\n\n"
                    "_Note:_\n"
                    "Ketik angka sesuai pilihan\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                return

            admin_task_in_progress["task_type"] = task_types[notification.message_text]
            notification.state_manager.update_state_data(
                notification.sender,
                {"state_history": history, "admin_task_in_progress": admin_task_in_progress}
            )
            
            notification.answer(
                "*📖 Masukkan Deskripsi Tugas:*\n\n"
                "_Note:_\n"
                "Ketik deskripsi tugas\n"
                "Ketik 0 untuk kembali ke Home"
            )
            update_state_with_history(notification, States.ADMIN_TASK_DESCRIPTION)

        @self.bot.router.message(
            type_message="textMessage",
            state=States.ADMIN_TASK_DESCRIPTION
        )
        def admin_task_description_handler(notification):
            """Handle task description input in admin flow"""
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            admin_task_in_progress = state_data.get("admin_task_in_progress", {})
            history = state_data.get("state_history", [])

            if notification.message_text == "0":
                notification.answer(
                    "*📂 Pilih Jenis Tugas:*\n\n"
                    "1. Mandiri\n"
                    "2. Kelompok\n"
                    "3. Ujian\n"
                    "4. Quiz\n"
                    "5. Project\n\n"
                    "_Note:_\n"
                    "Ketik angka sesuai pilihan\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                notification.state_manager.update_state_data(
                    notification.sender,
                    {"state_history": history, "admin_task_in_progress": admin_task_in_progress}
                )
                update_state_with_history(notification, States.ADMIN_TASK_TYPE)
                return
            
            admin_task_in_progress["task_description"] = notification.message_text.strip() # Can be empty if admin wishes
            notification.state_manager.update_state_data(
                notification.sender,
                {"state_history": history, "admin_task_in_progress": admin_task_in_progress}
            )
            
            notification.answer(
                "*⏰ Masukkan Deadline Tugas:*\n\n"
                "Format: DD-MM-YYYY HH:MM\n"
                "Contoh: 25-12-2023 23:59\n\n"
                "_Note:_\n"
                "Ketik deadline sesuai format\n"
                "Ketik 'ulang hari' untuk ganti hari pengumpulan\n" # Added this info
                "Ketik 0 untuk kembali ke Home"
            )
            update_state_with_history(notification, States.ADMIN_TASK_DEADLINE)

        @self.bot.router.message(
            type_message="textMessage",
            state=States.ADMIN_TASK_DEADLINE,
            regexp=r"^\s*[uU]lang hari\s*$" 
        )
        def admin_task_deadline_ulang_hari_handler(notification):
            """Handle 'ulang hari' input in ADMIN_TASK_DEADLINE state"""
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            admin_task_in_progress = state_data.get("admin_task_in_progress", {})
            history = state_data.get("state_history", [])

            days_response = supabase.table('days').select('id, name').order('id').execute()
            days = {str(item['id']): item['name'] for item in days_response.data}
            day_list = "\n".join([f"{num}. {name}" for num, name in days.items()])

            notification.answer(
                "*🗓️ Pilih Hari Pengumpulan Kembali:*\n\n" +
                day_list +
                "\n\n_Note:_\n"
                "Ketik angka sesuai pilihan\n"
                "Ketik 0 untuk kembali ke Home"
            )
            # Important: Persist existing admin_task_in_progress data when going back
            notification.state_manager.update_state_data(
                notification.sender,
                {"state_history": history, "admin_task_in_progress": admin_task_in_progress}
            )
            update_state_with_history(notification, States.ADMIN_DAY_SELECTION)


        @self.bot.router.message(
            type_message="textMessage",
            state=States.ADMIN_TASK_DEADLINE
        )
        def admin_task_deadline_handler(notification):
            """Handle task deadline input in admin flow"""
            state_data = notification.state_manager.get_state_data(notification.sender) or {}
            admin_task_in_progress = state_data.get("admin_task_in_progress")
            if not isinstance(admin_task_in_progress, dict):
                logger.error("admin_task_in_progress is not a dict or missing. Resetting flow.")
                self.start_add_task_flow(notification)
                return
                
            history = state_data.get("state_history", [])

            if notification.message_text == "0":
                notification.answer(
                    "*📖 Masukkan Deskripsi Tugas:*\n\n"
                    "_Note:_\n"
                    "Ketik deskripsi tugas\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                notification.state_manager.update_state_data(
                    notification.sender,
                    {"state_history": history, "admin_task_in_progress": admin_task_in_progress}
                )
                update_state_with_history(notification, States.ADMIN_TASK_DESCRIPTION)
                return

            try:
                # Parse the input as naive datetime
                naive_due_date = datetime.strptime(notification.message_text.strip(), "%d-%m-%Y %H:%M")
                # Make it timezone aware (WIB)
                aware_due_date = naive_due_date.replace(tzinfo=indonesia_tz)
                
                # Check if deadline is in the past
                if aware_due_date < datetime.now(indonesia_tz):
                    raise ValueError("Deadline tidak boleh di masa lalu")

                selected_day_id_str = admin_task_in_progress.get("selected_day_id")
                if not selected_day_id_str:
                     raise ValueError("selected_day_id missing from state")
                selected_day_id = int(selected_day_id_str)
                deadline_weekday = aware_due_date.weekday() + 1 

                if deadline_weekday != selected_day_id:
                    day_response = supabase.table("days").select("name").eq("id", selected_day_id).execute()
                    selected_day_name = day_response.data[0]["name"] if day_response.data else f"Hari ID {selected_day_id}"
                    notification.answer(
                        f"⚠️ *Input tidak valid!*\n\n"
                        f"Tanggal deadline yang kamu masukkan ({aware_due_date.strftime('%A, %d-%m-%Y')}) tidak jatuh pada hari {selected_day_name}.\n\n"
                        "Silakan:\n"
                        "1. Masukkan kembali deadline yang sesuai.\n"
                        "2. Ketik 'ulang hari' untuk memilih hari pengumpulan yang berbeda.\n"
                        "Ketik 0 untuk kembali."
                    )
                    return 
            except ValueError as e:
                logger.warning(f"Invalid deadline input or state issue: {e}")
                notification.answer(
                    f"⚠️ *Input tidak valid!* ({e})\n\n"
                    "*⏰ Masukkan Deadline Tugas:*\n\n"
                    "Format: DD-MM-YYYY HH:MM\n"
                    "Contoh: 25-12-2023 23:59\n\n"
                    "_Note:_\n"
                    "Ketik deadline sesuai format\n"
                    "Ketik 'ulang hari' untuk ganti hari pengumpulan\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                return
            
            admin_response = supabase.table("users").select("id").eq("phone_number", notification.sender).execute()
            if not admin_response.data:
                notification.answer("❌ Admin tidak ditemukan di database.")
                self.start_add_task_flow(notification) 
                return
            admin_id = admin_response.data[0]["id"]

            # Construct task_data with timezone-aware due_date
            task_to_save = {
                "class_id": int(admin_task_in_progress["selected_class_id"]),
                "day_id": int(admin_task_in_progress["selected_day_id"]),
                "name": admin_task_in_progress["task_name"],
                "description": admin_task_in_progress["task_description"],
                "jenis_tugas": admin_task_in_progress["task_type"],
                "due_date": aware_due_date.isoformat(), # This will include timezone info
                "created_by": admin_id
            }
            
            try:
                db_response = supabase.table("tasks").insert(task_to_save).execute()
                
                if db_response.data:
                    class_resp = supabase.table("classes").select("name").eq("id", task_to_save["class_id"]).execute()
                    class_name = class_resp.data[0]["name"] if class_resp.data else f"Kelas ID {task_to_save['class_id']}"
                    
                    day_resp = supabase.table("days").select("name").eq("id", task_to_save["day_id"]).execute()
                    day_name = day_resp.data[0]["name"] if day_resp.data else f"Hari ID {task_to_save['day_id']}"

                    notification.answer(
                        "✅ *Tugas berhasil ditambahkan!*\n\n"
                        f"📚 Kelas: {class_name}\n"
                        f"📅 Hari: {day_name}\n"
                        f"📝 Tugas: {task_to_save['name']}\n"
                        f"📂 Jenis: {task_to_save['jenis_tugas'].capitalize()}\n"
                        f"⏰ Deadline: {aware_due_date.strftime('%d %B %Y %H:%M')}"
                    )

                    # CRITICAL: Reset admin_task_in_progress after successful save, keeping history
                    notification.state_manager.update_state_data(
                        notification.sender,
                        {"state_history": history, "admin_task_in_progress": {}} 
                    )
                else:
                    logger.error(f"Failed to save task to DB: {db_response.error}")
                    notification.answer("❌ Gagal menyimpan tugas ke database. Error: " + (str(db_response.error) if db_response.error else "Unknown"))
            except Exception as e:
                logger.error(f"Error saving task: {e}")
                notification.answer(f"❌ Terjadi kesalahan saat menyimpan tugas: {e}")

            # Return to admin menu
            notification.answer(
                "*🛠️ Panel Ketua Kelas*\n\n"
                "1. Tambah Tugas Baru\n"
                "2. Kembali ke Menu Utama\n\n"
                "_Note:_\n"
                "Ketik angka sesuai pilihan\n"
                "Ketik 0 untuk kembali ke Home"
            )
            update_state_with_history(notification, States.ADMIN_MENU)

    def start_add_task_flow(self, notification):
        """Start the task addition flow by resetting temporary task data."""
        current_overall_state_data = notification.state_manager.get_state_data(notification.sender) or {}
        history = current_overall_state_data.get("state_history", [])

        # Initialize/reset the specific container for admin task creation data
        notification.state_manager.update_state_data(
            notification.sender, 
            {"state_history": history, "admin_task_in_progress": {}} # Key change: admin_task_in_progress is reset here
        )

        response = supabase.table('classes').select('id, name').order('id').execute()
        classes = {str(item['id']): item['name'] for item in response.data}
        class_list = "\n".join([f"{num}. {name}" for num, name in classes.items()])
        
        notification.answer(
            "*🧑‍🏫 Pilih Kelas:*\n\n" +
            class_list +
            "\n\n_Note:_\n"
            "Ketik angka sesuai pilihan\n"
            "Ketik 0 untuk kembali ke Home"
        )
        update_state_with_history(notification, States.ADMIN_CLASS_SELECTION)

    # show_admin_list method can remain as is, it doesn't interact with this specific state issue.