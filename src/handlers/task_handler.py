from datetime import datetime
from typing import List, Dict
from ..config import States, supabase
from ..utils import update_state_with_history, calculate_notification_times, save_notification
import asyncio
import logging

try:
    from zoneinfo import ZoneInfo
    utc_tz = ZoneInfo("UTC")
    indonesia_tz = ZoneInfo("Asia/Jakarta")
except ImportError:
    import pytz
    utc_tz = pytz.utc
    indonesia_tz = pytz.timezone("Asia/Jakarta")

logger = logging.getLogger(__name__)

class TaskHandler:
    def __init__(self, bot):
        self.bot = bot
        self.setup_handlers()

    def setup_handlers(self):
        """Setup all task-related message handlers"""
        @self.bot.router.message(
            type_message="textMessage",
            state=States.CLASS_SELECTION
        )
        def class_selection_state_handler(notification):
            """Handle all messages in CLASS_SELECTION state"""
            if notification.message_text == "0":
                notification.answer(
                    "*Hi, Skremates!* 💸\n\n"
                    "Selamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\n"
                    
                    "Apa yang ingin kamu akses?\n\n"
                    
                    "1. Lihat Tugas\n"
                    "2. Panel Ketua Kelas\n\n"
                    "Ketik angka pilihan kamu *(1-2)*"
                )
                notification.state_manager.update_state(notification.sender, States.INITIAL)
            elif notification.message_text in [str(i) for i in range(1, 9)]:
                self.class_selection_handler(notification)
            else:
                self.show_invalid_message(notification, States.CLASS_SELECTION)

        @self.bot.router.message(
            type_message="textMessage",
            state=States.DAY_SELECTION
        )
        def day_selection_state_handler(notification):
            """Handle all messages in DAY_SELECTION state"""
            if notification.message_text == "0":
                notification.answer(
                    "*Hi, Skremates!* 💸\n\n"
                    "Selamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\n"
                    
                    "Apa yang ingin kamu akses?\n\n"
                    
                    "1. Lihat Tugas\n"
                    "2. Panel Ketua Kelas\n\n"
                    "Ketik angka pilihan kamu *(1-2)*"
                )
                notification.state_manager.update_state(notification.sender, States.INITIAL)
            elif notification.message_text in [str(i) for i in range(1, 8)]:
                self.day_selection_handler(notification)
            else:
                self.show_invalid_message(notification, States.DAY_SELECTION)

        @self.bot.router.message(
            type_message="textMessage",
            state=States.TASK_LIST
        )
        def task_list_state_handler(notification):
            """Handle all messages in TASK_LIST state"""
            if notification.message_text == "0":
                notification.answer(
                    "*Hi, Skremates!* 💸\n\n"
                    "Selamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\n"
                    
                    "Apa yang ingin kamu akses?\n\n"
                    
                    "1. Lihat Tugas\n"
                    "2. Panel Ketua Kelas\n\n"
                    "Ketik angka pilihan kamu *(1-2)*"
                )
                notification.state_manager.update_state(notification.sender, States.INITIAL)
            elif notification.message_text.isdigit():
                state_data = notification.state_manager.get_state_data(notification.sender)
                tasks = state_data.get("tasks", [])
                task_idx = int(notification.message_text) - 1
                if 0 <= task_idx < len(tasks):
                    self.task_detail_handler(notification)
                else:
                    self.show_invalid_message(notification, States.TASK_LIST)
            else:
                self.show_invalid_message(notification, States.TASK_LIST)

        @self.bot.router.message(
            type_message="textMessage",
            state=States.NOTIFICATION_SETUP
        )
        def notification_setup_state_handler(notification):
            """Handle all messages in NOTIFICATION_SETUP state"""
            if notification.message_text == "0":
                notification.answer(
                    "*Hi, Skremates!* 💸\n\n"
                    "Selamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\n"
                    
                    "Apa yang ingin kamu akses?\n\n"
                    
                    "1. Lihat Tugas\n"
                    "2. Panel Ketua Kelas\n\n"
                    "Ketik angka pilihan kamu *(1-2)*"
                )
                notification.state_manager.update_state(notification.sender, States.INITIAL)
            elif notification.message_text == "1":
                # Send immediate response
                notification.answer(
                    "⏳ *Mengatur reminder...*\n\n"
                    "Mohon tunggu sebentar..."
                )
                
                # Get task data immediately
                state_data = notification.state_manager.get_state_data(notification.sender)
                task = state_data.get("selected_task")
                
                if not task:
                    notification.answer("❌ Terjadi kesalahan: Data tugas tidak ditemukan")
                    return
                
                # Calculate notification times
                due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                notify_times = calculate_notification_times(due_date)
                
                # Save to database immediately
                try:
                    response = supabase.table('notifications').insert({
                        "phone_number": notification.sender,
                        "task_id": task['id'],
                        "notification_times": notify_times,
                        "is_sent": False
                    }).execute()
                    
                    if response.data:
                        notification.answer(
                            "✅ *Reminder berhasil diatur!*\n\n"
                            f"Kamu akan menerima reminder untuk tugas:\n"
                            f"📝 {task['name']}\n\n"
                            "Reminder akan dikirim:\n"
                            "- 3 hari sebelum\n"
                            "- 1 hari sebelum\n"
                            "- 1 jam sebelum"
                        )
                        # Show task menu after setting reminder
                        notification.answer(
                            "*Hi, Skremates!* 💸\n\n"
                            "Selamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\n"
                            
                            "Apa yang ingin kamu akses?\n\n"
                            
                            "1. Lihat Tugas\n"
                            "2. Panel Ketua Kelas\n\n"
                            "Ketik angka pilihan kamu *(1-2)*"
                        )
                        notification.state_manager.update_state(notification.sender, States.INITIAL)
                    else:
                        notification.answer(
                            "❌ *Gagal menyimpan notifikasi*\n\n"
                            "Silakan coba lagi nanti atau hubungi admin jika masalah berlanjut."
                        )
                except Exception as e:
                    logger.error(f"Error saving notification: {e}")
                    notification.answer(
                        "❌ *Terjadi kesalahan*\n\n"
                        "Gagal mengatur reminder. Silakan coba lagi nanti."
                    )
            elif notification.message_text == "2":
                self.skip_reminder_handler(notification)
            else:
                self.show_invalid_message(notification, States.NOTIFICATION_SETUP)

    def start_flow_handler(self, notification):
        """Start the task viewing flow"""
        response = supabase.table('classes').select('id, name').order('id').execute()
        classes = {str(item['id']): item['name'] for item in response.data}
        
        class_list = "\n".join([f"{num}. {name}" for num, name in classes.items()])
        
        notification.answer(
            "🧑‍🏫 *Pilih Kelasmu:* 👩‍🏫\n\n" +
            class_list +
            "\n\n_Note:_\n"
            "Ketik angka sesuai pilihan\n"
            "Ketik 0 untuk kembali ke Home"
        )
        
        update_state_with_history(notification, States.CLASS_SELECTION)

    def class_selection_handler(self, notification):
        """Handle valid class selection"""
        try:
            selected_class_id = notification.message_text
            
            # Get days from database
            days_response = supabase.table('days').select('id, name').order('id').execute()
            days = {str(item['id']): item['name'] for item in days_response.data}
            
            day_list = "\n".join([f"{num}. {name}" for num, name in days.items()])
            
            notification.state_manager.update_state_data(
                notification.sender,
                {
                    "selected_class_id": selected_class_id,
                    **notification.state_manager.get_state_data(notification.sender)
                }
            )
            
            notification.answer(
                "*🗓️ Pilih Hari Pengumpulan: 🗓️*\n\n" +
                day_list +
                "\n\n_Note:_\n"
                "Ketik angka sesuai pilihan\n"
                "Ketik 0 untuk kembali ke Home"
            )
            
            update_state_with_history(notification, States.DAY_SELECTION)
            
        except Exception as e:
            logger.error(f"[TASK] Error in class selection: {e}")
            notification.answer("Terjadi error, silakan coba lagi")

    def day_selection_handler(self, notification):
        """Handle valid day selection"""
        try:
            selected_day_id = notification.message_text
            
            state_data = notification.state_manager.get_state_data(notification.sender)
            selected_class_id_str = state_data.get("selected_class_id")
            
            if not selected_class_id_str:
                notification.answer("Terjadi kesalahan: Kelas belum dipilih. Silakan ulangi dari awal.")
                self.start_flow_handler(notification)
                return

            try:
                selected_class_id = int(selected_class_id_str)
            except ValueError:
                notification.answer("Terjadi kesalahan: Format ID kelas tidak valid. Silakan ulangi.")
                self.start_flow_handler(notification)
                return
            
            # Get day name
            day_response = supabase.table('days').select('name').eq('id', int(selected_day_id)).execute()
            day_name = day_response.data[0]['name']
            
            # Get tasks from database
            query = supabase.table('tasks').select('*, classes(name), days(name)') \
                .eq('class_id', selected_class_id) \
                .eq('day_id', int(selected_day_id)) \
                .order('due_date')
            
            tasks_response = query.execute()
            tasks = tasks_response.data
            
            if not tasks:
                notification.answer(
                    f"📭 Yeay! Tidak ada tugas untuk hari {day_name}"
                )
                # Show task menu after no tasks found
                notification.answer(
                    "*Hi, Skremates!* 💸\n\n"
                    "Selamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\n"
                    
                    "Apa yang ingin kamu akses?\n\n"
                    
                    "1. Lihat Tugas\n"
                    "2. Panel Ketua Kelas\n\n"
                    "Ketik angka pilihan kamu *(1-2)*"
                )
                notification.state_manager.update_state(notification.sender, States.INITIAL)
                return
            
            # Store tasks in state
            notification.state_manager.update_state_data(
                notification.sender,
                {
                    "tasks": tasks,
                    "selected_day_id": selected_day_id,
                    "selected_class_id": str(selected_class_id),
                    "state_history": (notification.state_manager.get_state_data(notification.sender) or {}).get("state_history", [])
                }
            )
            
            # Format tasks list
            tasks_list = ""
            for idx, task in enumerate(tasks, 1):
                # Convert UTC to WIB
                due_date_utc = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                due_date_wib = due_date_utc.astimezone(indonesia_tz)
                due_date_str = due_date_wib.strftime('%d/%m/%Y %H:%M WIB')
                tasks_list += (
                    f"{idx}. {task['name']}\n"
                    f"🗒️ {task['description']}\n"
                    f"⏰ {due_date_str}\n\n"
                )
            
            notification.answer(
                f"📚 Tugas untuk hari *{day_name}*:\n\n" +
                tasks_list +
                "_Note:_\n"
                "Ketik angka sesuai pilihan\n"
                "Ketik 0 untuk kembali ke Home"
            )    
            
            update_state_with_history(notification, States.TASK_LIST)
            
        except Exception as e:
            logger.error(f"[TASK] Error in day selection: {e}")
            notification.answer("Terjadi error, silakan coba lagi")

    def task_detail_handler(self, notification):
        """Show task details"""
        try:
            task_idx = int(notification.message_text) - 1
            
            state_data = notification.state_manager.get_state_data(notification.sender)
            tasks = state_data.get("tasks", [])
            
            if not (0 <= task_idx < len(tasks)):
                self.show_invalid_message(notification, States.TASK_LIST)
                return
                
            task = tasks[task_idx]
            
            if 'due_date' not in task or not task['due_date']:
                notification.answer("Terjadi kesalahan: Informasi deadline tugas tidak lengkap.")
                self.day_selection_handler(notification)
                return

            # Convert UTC to WIB
            due_date_utc = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
            due_date_wib = due_date_utc.astimezone(indonesia_tz)
            due_date_str = due_date_wib.strftime('%d/%m/%Y %H:%M WIB')
            
            message = (
                f"📚 *Detail Tugas:*\n\n"
                f"📝 *Nama:* {task.get('name', 'N/A')}\n"
                f"📖 *Deskripsi:* {task.get('description', 'N/A')}\n"
                f"⏰ *Deadline:* {due_date_str}\n"
                f"📂 *Jenis:* {task.get('jenis_tugas', 'N/A').capitalize()}\n\n"
                "Apakah ingin diingatkan untuk tugas ini?\n"
                "1. ✅ Ya\n"
                "2. ❌ Tidak\n"
                "0. Kembali ke Menu Utama\n\n"
                "_Note:_\n"
                "Ketik angka sesuai pilihan\n"
                "Ketik 0 untuk kembali ke Home"
            )
            
            notification.state_manager.update_state_data(
                notification.sender,
                {
                    "selected_task": task,
                    "tasks": tasks,
                    "selected_day_id": state_data.get("selected_day_id"),
                    "selected_class_id": state_data.get("selected_class_id"),
                    "state_history": state_data.get("state_history", [])
                }
            )
            
            update_state_with_history(notification, States.NOTIFICATION_SETUP)
            notification.answer(message)
            
        except Exception as e:
            logger.error(f"[TASK] Error in task detail: {e}")
            notification.answer("Terjadi error, silakan coba lagi")

    def skip_reminder_handler(self, notification):
        """Handle when user chooses not to set reminder"""
        notification.answer(
            "ℹ️ Tidak ada reminder yang diatur untuk tugas ini."
        )
        # Show task menu after skipping reminder
        notification.answer(
            "*Hi, Skremates!* 💸\n\n"
            "Selamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\n"
            
            "Apa yang ingin kamu akses?\n\n"
            
            "1. Lihat Tugas\n"
            "2. Panel Ketua Kelas\n\n"
            "Ketik angka pilihan kamu *(1-2)*"
        )
        notification.state_manager.update_state(notification.sender, States.INITIAL)

    def show_invalid_message(self, notification, current_state: str):
        """Show invalid input message and repeat current options"""
        state_data = notification.state_manager.get_state_data(notification.sender) or {}
        
        if current_state == States.INITIAL:
            notification.answer(
                "⚠️ *Input tidak valid!*\n\n"
                "*Hi, Skremates!* 💸\n\n"
                "Selamat datang di *Crealert: Your Weekly Task Reminder* 🔔! \n\n"
                
                "Apa yang ingin kamu akses?\n\n"
                
                "1. Lihat Tugas\n"
                "2. Panel Ketua Kelas\n\n"
                "Ketik angka pilihan kamu *(1-2)*"
            )
        elif current_state == States.CLASS_SELECTION:
            response = supabase.table('classes').select('id, name').order('id').execute()
            classes = {str(item['id']): item['name'] for item in response.data}
            class_list = "\n".join([f"{num}. {name}" for num, name in classes.items()])
            
            notification.answer(
                "⚠️ *Input tidak valid!*\n\n"
                "🧑‍🏫 *Pilih Kelasmu:* 👩‍🏫\n\n" +
                class_list +
                "\n\n_Note:_\n"
                "Ketik angka sesuai pilihan\n"
                "Ketik 0 untuk kembali ke Home"
            )
        elif current_state == States.DAY_SELECTION:
            days_response = supabase.table('days').select('id, name').order('id').execute()
            days = {str(item['id']): item['name'] for item in days_response.data}
            day_list = "\n".join([f"{num}. {name}" for num, name in days.items()])
            
            notification.answer(
                "⚠️ *Input tidak valid!*\n\n"
                "*🗓️ Pilih Hari Pengumpulan: 🗓️*\n\n" +
                day_list +
                "\n\n_Note:_\n"
                "Ketik angka sesuai pilihan\n"
                "Ketik 0 untuk kembali ke Home"
            )
        elif current_state == States.TASK_LIST:
            tasks = state_data.get("tasks", [])
            selected_day_id = state_data.get("selected_day_id")
            day_response = supabase.table('days').select('name').eq('id', selected_day_id).execute()
            day_name = day_response.data[0]['name']
            
            tasks_list = ""
            for idx, task in enumerate(tasks, 1):
                due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                due_date_str = due_date.strftime('%d/%m/%Y %H:%M')
                tasks_list += (
                    f"{idx}. {task['name']}\n"
                    f"🗒️ {task['description']}\n"
                    f"⏰ {due_date_str}\n\n"
                )
            
            notification.answer(
                "⚠️ *Input tidak valid!*\n\n"
                f"📚 Tugas untuk hari *{day_name}*:\n\n" +
                tasks_list +
                "_Note:_\n"
                "Ketik angka sesuai pilihan\n"
                "Ketik 0 untuk kembali ke Home"
            )
        elif current_state == States.NOTIFICATION_SETUP:
            task = state_data.get("selected_task")
            due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
            due_date_str = due_date.strftime('%d/%m/%Y %H:%M')
            
            notification.answer(
                "⚠️ *Input tidak valid!*\n\n"
                f"📚 *Detail Tugas:*\n\n"
                f"📝 *Nama:* {task['name']}\n"
                f"📖 *Deskripsi:* {task['description']}\n"
                f"⏰ *Deadline:* {due_date_str}\n"
                f"📂 *Jenis:* {task['jenis_tugas'].capitalize()}\n\n"
                "Apakah ingin diingatkan untuk tugas ini?\n"
                "1. ✅ Ya\n"
                "2. ❌ Tidak\n"
                "0. Kembali ke Menu Utama\n\n"
                "_Note:_\n"
                "Ketik angka sesuai pilihan\n"
                "Ketik 0 untuk kembali ke Home"
            ) 