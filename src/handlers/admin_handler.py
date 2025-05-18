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
                    "Maaf, kamu tidak memiliki akses ke menu admin.\n"
                    "Silakan pilih menu lain."
                )
                return
            
            notification.answer(
                "*🛠️ Menu Admin*\n\n"
                "1. Tambah Tugas Baru\n"
                "2. Lihat Daftar Admin\n"
                "3. Kembali ke Menu Utama\n\n"
                "Ketik pilihan kamu (1-3)"
            )
            update_state_with_history(notification, States.ADMIN_MENU)

        @self.bot.router.message(
            type_message="textMessage",
            state=States.ADMIN_MENU,
            regexp=r"^3$"
        )
        def admin_menu_back_handler(notification):
            """Handle back navigation from admin menu"""
            # Return to main menu
            notification.answer(
                "*Hallo Skremates!* 👋🏻\n"
                "*Selamat datang di Crealert!* 🚨📖\n"
                "_Siap bantu kamu tetap on track dan bebas dari tugas yang kelupaan._\n"
                "*Yuk mulai cek list tugasmu hari ini!*\n\n"
                "Silakan pilih menu:\n"
                "1. Lihat Tugas\n"
                "2. Menu Admin\n\n"
                "Ketik angka pilihan kamu *(1-2)*"
            )
            notification.state_manager.update_state(notification.sender, States.INITIAL)

        @self.bot.router.message(
            type_message="textMessage",
            state=States.ADMIN_MENU,
            regexp=r"^(1|2)$"
        )
        def admin_menu_selection_handler(notification):
            """Handle admin menu selections"""
            if notification.message_text == "1":
                self.start_add_task_flow(notification)
            elif notification.message_text == "2":
                self.show_admin_list(notification)
            else:
                notification.answer(
                    "⚠️ *Input tidak valid*\n\n"
                    "Silakan pilih menu admin:\n"
                    "1. Tambah Tugas Baru\n"
                    "2. Lihat Daftar Admin\n"
                    "3. Kembali ke Menu Utama\n\n"
                    "Ketik pilihan kamu (1-3)"
                )

        @self.bot.router.message(
            type_message="textMessage",
            state=States.ADMIN_ADD_TASK
        )
        def handle_task_input(notification):
            """Handle task data input"""
            if notification.message_text.lower() == "batal":
                # Return to admin menu
                notification.answer(
                    "*🛠️ Menu Admin*\n\n"
                    "1. Tambah Tugas Baru\n"
                    "2. Lihat Daftar Admin\n"
                    "3. Kembali ke Menu Utama\n\n"
                    "Ketik pilihan kamu (1-3)"
                )
                update_state_with_history(notification, States.ADMIN_MENU)
                return
            
            try:
                # Parse input
                parts = notification.message_text.split("|")
                if len(parts) != 6:
                    raise ValueError("Format harus terdiri dari 6 bagian dipisahkan oleh |")
                
                class_id, day_id, name, description, jenis, due_date_str = parts
                
                # Validasi input
                if not class_id.isdigit() or int(class_id) not in range(1, 9):
                    raise ValueError("Kelas harus angka antara 1-8")
                
                if not day_id.isdigit() or int(day_id) not in range(1, 8):
                    raise ValueError("Hari harus angka antara 1-7")
                
                if not name.strip():
                    raise ValueError("Nama tugas tidak boleh kosong")
                
                jenis_tugas = jenis.lower().strip()
                if jenis_tugas not in ['mandiri', 'kelompok', 'ujian']:
                    raise ValueError("Jenis tugas harus mandiri/kelompok/ujian")
                
                try:
                    due_date = datetime.strptime(due_date_str, "%d-%m-%Y %H:%M")
                    if due_date < datetime.now():
                        raise ValueError("Deadline tidak boleh di masa lalu")
                except ValueError:
                    raise ValueError("Format deadline harus DD-MM-YYYY HH:MM")

                # Dapatkan admin_id dari database
                admin_response = supabase.table("users") \
                    .select("id") \
                    .eq("phone_number", notification.sender) \
                    .execute()
                
                if not admin_response.data:
                    raise ValueError("Admin tidak ditemukan di database")
                
                admin_id = admin_response.data[0]["id"]

                # Simpan ke database
                task_data = {
                    "class_id": int(class_id),
                    "day_id": int(day_id),
                    "name": name.strip(),
                    "description": description.strip(),
                    "jenis_tugas": jenis_tugas,
                    "due_date": due_date.isoformat(),
                    "created_by": admin_id
                }
                
                response = supabase.table("tasks").insert(task_data).execute()
                
                if response.data:
                    # Get class and day names for confirmation message
                    class_response = supabase.table("classes") \
                        .select("name") \
                        .eq("id", class_id) \
                        .execute()
                    class_name = class_response.data[0]["name"] if class_response.data else f"Kelas {class_id}"
                    
                    day_response = supabase.table("days") \
                        .select("name") \
                        .eq("id", day_id) \
                        .execute()
                    day_name = day_response.data[0]["name"] if day_response.data else f"Hari {day_id}"

                    notification.answer(
                        "✅ *Tugas berhasil ditambahkan!*\n\n"
                        f"📚 Kelas: {class_name}\n"
                        f"📅 Hari: {day_name}\n"
                        f"📝 Tugas: {name.strip()}\n"
                        f"📂 Jenis: {jenis_tugas.capitalize()}\n"
                        f"⏰ Deadline: {due_date.strftime('%d %B %Y %H:%M')}"
                    )
                else:
                    notification.answer("❌ Gagal menyimpan tugas ke database")
                    
            except Exception as e:
                error_msg = str(e)
                notification.answer(
                    f"⚠️ *Error:* {error_msg}\n\n"
                    "Format yang benar:\n"
                    "*Kelas|Hari|Nama Tugas|Deskripsi|Jenis|Deadline*\n\n"
                    "Contoh:\n"
                    "3|2|Laporan Praktikum|Buat laporan praktikum minggu 5|mandiri|25-12-2023 23:59\n\n"
                    "Keterangan:\n"
                    "- Kelas: 1-8\n"
                    "- Hari: 1-7\n"
                    "- Jenis: mandiri/kelompok/ujian\n"
                    "- Deadline: DD-MM-YYYY HH:MM"
                )
            
            # Kembali ke menu admin
            update_state_with_history(notification, States.ADMIN_MENU)
            notification.answer(
                "*🛠️ Menu Admin*\n\n"
                "1. Tambah Tugas Baru\n"
                "2. Lihat Daftar Admin\n"
                "3. Kembali ke Menu Utama\n\n"
                "Ketik pilihan kamu (1-3)"
            )

    def start_add_task_flow(self, notification):
        """Start simplified task addition flow"""
        notification.answer(
            "📝 *Tambah Tugas Baru*\n\n"
            "Silakan kirim data tugas dalam format berikut:\n\n"
            "*Kelas|Hari|Nama Tugas|Deskripsi|Jenis|Deadline*\n\n"
            "Contoh:\n"
            "3|2|Laporan Praktikum|Buat laporan praktikum minggu 5|mandiri|25-12-2023 23:59\n\n"
            "Keterangan:\n"
            "- Kelas:\n"
            "  1. 2022A\n"
            "  2. 2022B\n"
            "  3. 2023A\n"
            "  4. 2023B\n"
            "  5. 2023C\n"
            "  6. 2024A\n"
            "  7. 2024B\n"
            "  8. 2024C\n\n"
            "- Hari:\n"
            "  1. Senin\n"
            "  2. Selasa\n"
            "  3. Rabu\n"
            "  4. Kamis\n"
            "  5. Jumat\n"
            "  6. Sabtu\n"
            "  7. Minggu"
        )
        update_state_with_history(notification, States.ADMIN_ADD_TASK)

    def show_admin_list(self, notification):
        """Show list of admin phone numbers"""
        admin_list = "\n".join([f"- {phone}" for phone in ADMIN_PHONES])
        notification.answer(
            "*📋 Daftar Admin:*\n\n" +
            admin_list
        )
        update_state_with_history(notification, States.ADMIN_MENU)
        notification.answer(
            "*🛠️ Menu Admin*\n\n"
            "1. Tambah Tugas Baru\n"
            "2. Lihat Daftar Admin\n"
            "3. Kembali ke Menu Utama\n\n"
            "Ketik pilihan kamu (1-3)"
        ) 