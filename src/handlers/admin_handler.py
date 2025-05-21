from datetime import datetime
from typing import List, Dict
import logging
from ..config import States, supabase, is_admin, ADMIN_PHONES
from ..utils import update_state_with_history

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
            # Return to main menu
            notification.answer(
                "*Hi, Skremates!* 💸\n\n"
                "*Selamat datang di *Crealert: Your Weekly Task Reminder* 🔔!* \n\n"
                
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
            if notification.message_text == "0":
                notification.answer(
                    "*🛠️ Panel Ketua Kelas*\n\n"
                    "1. Tambah Tugas Baru\n"
                    "2. Kembali ke Menu Utama\n\n"
                    "_Note:_\n"
                    "Ketik angka sesuai pilihan\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                update_state_with_history(notification, States.ADMIN_MENU)
                return

            if not notification.message_text.isdigit() or int(notification.message_text) not in range(1, 9):
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

            notification.state_manager.update_state_data(
                notification.sender,
                {
                    "selected_class_id": notification.message_text,
                    **notification.state_manager.get_state_data(notification.sender)
                }
            )
            
            # Get days from database
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
            if notification.message_text == "0":
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
                return

            if not notification.message_text.isdigit() or int(notification.message_text) not in range(1, 8):
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

            notification.state_manager.update_state_data(
                notification.sender,
                {
                    "selected_day_id": notification.message_text,
                    **notification.state_manager.get_state_data(notification.sender)
                }
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

            notification.state_manager.update_state_data(
                notification.sender,
                {
                    "task_name": notification.message_text.strip(),
                    **notification.state_manager.get_state_data(notification.sender)
                }
            )
            
            notification.answer(
                "*📂 Pilih Jenis Tugas:*\n\n"
                "1. Mandiri\n"
                "2. Kelompok\n"
                "3. Ujian\n\n"
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
            if notification.message_text == "0":
                notification.answer(
                    "*📝 Masukkan Nama Tugas:*\n\n"
                    "_Note:_\n"
                    "Ketik nama tugas\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                update_state_with_history(notification, States.ADMIN_TASK_NAME)
                return

            task_types = {
                "1": "mandiri",
                "2": "kelompok",
                "3": "ujian"
            }

            if notification.message_text not in task_types:
                notification.answer(
                    "⚠️ *Input tidak valid!*\n\n"
                    "*📂 Pilih Jenis Tugas:*\n\n"
                    "1. Mandiri\n"
                    "2. Kelompok\n"
                    "3. Ujian\n\n"
                    "_Note:_\n"
                    "Ketik angka sesuai pilihan\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                return

            notification.state_manager.update_state_data(
                notification.sender,
                {
                    "task_type": task_types[notification.message_text],
                    **notification.state_manager.get_state_data(notification.sender)
                }
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
            if notification.message_text == "0":
                notification.answer(
                    "*📂 Pilih Jenis Tugas:*\n\n"
                    "1. Mandiri\n"
                    "2. Kelompok\n"
                    "3. Ujian\n\n"
                    "_Note:_\n"
                    "Ketik angka sesuai pilihan\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                update_state_with_history(notification, States.ADMIN_TASK_TYPE)
                return

            notification.state_manager.update_state_data(
                notification.sender,
                {
                    "task_description": notification.message_text.strip(),
                    **notification.state_manager.get_state_data(notification.sender)
                }
            )
            
            notification.answer(
                "*⏰ Masukkan Deadline Tugas:*\n\n"
                "Format: DD-MM-YYYY HH:MM\n"
                "Contoh: 25-12-2023 23:59\n\n"
                "_Note:_\n"
                "Ketik deadline sesuai format\n"
                "Ketik 0 untuk kembali ke Home"
            )
            update_state_with_history(notification, States.ADMIN_TASK_DEADLINE)

        @self.bot.router.message(
            type_message="textMessage",
            state=States.ADMIN_TASK_DEADLINE
        )
        def admin_task_deadline_handler(notification):
            """Handle task deadline input in admin flow"""
            if notification.message_text == "0":
                notification.answer(
                    "*📖 Masukkan Deskripsi Tugas:*\n\n"
                    "_Note:_\n"
                    "Ketik deskripsi tugas\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                update_state_with_history(notification, States.ADMIN_TASK_DESCRIPTION)
                return

            try:
                due_date = datetime.strptime(notification.message_text, "%d-%m-%Y %H:%M")
                if due_date < datetime.now():
                    raise ValueError("Deadline tidak boleh di masa lalu")
            except ValueError as e:
                notification.answer(
                    "⚠️ *Input tidak valid!*\n\n"
                    "*⏰ Masukkan Deadline Tugas:*\n\n"
                    "Format: DD-MM-YYYY HH:MM\n"
                    "Contoh: 25-12-2023 23:59\n\n"
                    "_Note:_\n"
                    "Ketik deadline sesuai format\n"
                    "Ketik 0 untuk kembali ke Home"
                )
                return

            # Get all task data from state
            state_data = notification.state_manager.get_state_data(notification.sender)
            
            # Get admin_id from database
            admin_response = supabase.table("users") \
                .select("id") \
                .eq("phone_number", notification.sender) \
                .execute()
            
            if not admin_response.data:
                notification.answer("❌ Admin tidak ditemukan di database")
                return
            
            admin_id = admin_response.data[0]["id"]

            # Prepare task data
            task_data = {
                "class_id": int(state_data["selected_class_id"]),
                "day_id": int(state_data["selected_day_id"]),
                "name": state_data["task_name"],
                "description": state_data["task_description"],
                "jenis_tugas": state_data["task_type"],
                "due_date": due_date.isoformat(),
                "created_by": admin_id
            }
            
            # Save to database
            try:
                response = supabase.table("tasks").insert(task_data).execute()
                
                if response.data:
                    # Get class and day names for confirmation message
                    class_response = supabase.table("classes") \
                        .select("name") \
                        .eq("id", state_data["selected_class_id"]) \
                        .execute()
                    class_name = class_response.data[0]["name"] if class_response.data else f"Kelas {state_data['selected_class_id']}"
                    
                    day_response = supabase.table("days") \
                        .select("name") \
                        .eq("id", state_data["selected_day_id"]) \
                        .execute()
                    day_name = day_response.data[0]["name"] if day_response.data else f"Hari {state_data['selected_day_id']}"

                    notification.answer(
                        "✅ *Tugas berhasil ditambahkan!*\n\n"
                        f"📚 Kelas: {class_name}\n"
                        f"📅 Hari: {day_name}\n"
                        f"📝 Tugas: {state_data['task_name']}\n"
                        f"📂 Jenis: {state_data['task_type'].capitalize()}\n"
                        f"⏰ Deadline: {due_date.strftime('%d %B %Y %H:%M')}"
                    )
                else:
                    notification.answer("❌ Gagal menyimpan tugas ke database")
            except Exception as e:
                logger.error(f"Error saving task: {e}")
                notification.answer("❌ Terjadi kesalahan saat menyimpan tugas")

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
        """Start the task addition flow"""
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

    def show_admin_list(self, notification):
        """Show list of admin phone numbers"""
        admin_list = "\n".join([f"- {phone}" for phone in ADMIN_PHONES])
        notification.answer(
            "*📋 Daftar Admin:*\n\n" +
            admin_list
        )
        update_state_with_history(notification, States.ADMIN_MENU)
        notification.answer(
            "*🛠️ Panel Ketua Kelas*\n\n"
            "1. Tambah Tugas Baru\n"
            "2. Kembali ke Menu Utama\n\n"
            "Ketik pilihan kamu (1-2)"
        ) 