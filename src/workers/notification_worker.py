import asyncio
from datetime import datetime
import logging
from typing import List, Dict # Anda memiliki ini, jadi saya biarkan
# Pastikan path impor ini benar sesuai struktur folder Anda:
# Jika config.py ada di src/, dan file ini di src/workers/, maka ..config sudah benar
from ..config import supabase
# GreenAPIBot mungkin tidak perlu diimpor di sini jika hanya untuk type hint di __init__
# from whatsapp_chatbot_python import GreenAPIBot


# Setup logger untuk modul ini
logger = logging.getLogger(__name__)
logger.info("NotificationWorker module: Logger configured.")

# Definisikan timezone object di level modul agar pasti tersedia dan di-log saat impor
try:
    from zoneinfo import ZoneInfo
    UTC_TZ_FOR_WORKER = ZoneInfo("UTC")
    INDONESIA_TZ_FOR_WORKER = ZoneInfo("Asia/Jakarta")
    logger.info("NotificationWorker module: Successfully imported timezone using zoneinfo.")
except ImportError:
    import pytz
    UTC_TZ_FOR_WORKER = pytz.utc
    INDONESIA_TZ_FOR_WORKER = pytz.timezone("Asia/Jakarta")
    logger.info("NotificationWorker module: Successfully imported timezone using pytz.")

# Cek impor supabase
logger.info("NotificationWorker module: Supabase client imported/configured check: supabase is not None -> %s", supabase is not None)

class NotificationWorker:
    def __init__(self, bot): # Anda bisa menambahkan type hint: bot: GreenAPIBot
        self.bot = bot
        self.running = False
        self.task = None
        logger.info("NotificationWorker class: Instance initialized.")

    async def start(self):
        """Start the notification worker"""
        if self.running:
            logger.info("NotificationWorker.start: Worker already running.")
            return self.task # Kembalikan task yang sudah ada jika sudah berjalan
        
        self.running = True
        logger.info("NotificationWorker.start: Worker flag set to running. Attempting to create _run task.")
        try:
            self.task = asyncio.create_task(self._run())
            logger.info("NotificationWorker.start: asyncio.create_task(self._run()) called successfully. Task created.")
        except Exception as e_create_task:
            logger.error(f"NotificationWorker.start: FAILED to create_task for _run: {e_create_task}", exc_info=True)
            self.running = False # Reset flag jika gagal membuat task
            self.task = None
        return self.task

    async def stop(self):
        """Stop the notification worker"""
        logger.info("NotificationWorker.stop: Attempting to stop worker.")
        self.running = False # Set flag untuk menghentikan loop di _run
        if self.task and not self.task.done(): # Periksa apakah task ada dan belum selesai
            logger.info("NotificationWorker.stop: Cancelling worker task.")
            self.task.cancel()
            try:
                await self.task
                logger.info("NotificationWorker.stop: Worker task awaited after cancellation.")
            except asyncio.CancelledError:
                logger.info("NotificationWorker.stop: Worker task successfully cancelled and caught CancelledError.")
            except Exception as e:
                logger.error(f"NotificationWorker.stop: Error encountered while awaiting cancelled task: {e}", exc_info=True)
        elif self.task and self.task.done():
            logger.info("NotificationWorker.stop: Worker task was already done.")
        else:
            logger.info("NotificationWorker.stop: No active task to cancel.")
        self.task = None
        logger.info("NotificationWorker.stop: Worker stopped.")

    async def _run(self):
        """Main worker loop"""
        # Log paling atas untuk memastikan metode ini dimasuki
        logger.info("NotificationWorker._run: Method entered. self.running is %s", self.running)
        
        try:
            # Log akses ke objek global/modul
            logger.info(f"NotificationWorker._run: Timezone objects successfully accessed - UTC: {UTC_TZ_FOR_WORKER}, WIB: {INDONESIA_TZ_FOR_WORKER}")
            logger.info(f"NotificationWorker._run: Supabase client accessible: {supabase is not None}")
            
            while self.running:
                current_time_utc = datetime.now(UTC_TZ_FOR_WORKER)
                logger.info(f"NotificationWorker: New cycle starting. Current UTC time for checks: {current_time_utc.isoformat()}")
                
                try:
                    logger.debug("NotificationWorker: Fetching unsent notifications from database...")
                    response = supabase.table('notifications') \
                        .select('id, phone_number, notification_times, task_id, tasks(id, name, description, due_date, jenis_tugas)') \
                        .eq('is_sent', False) \
                        .execute()
                    
                    if hasattr(response, 'error') and response.error:
                        logger.error(f"NotificationWorker: Supabase error fetching notifications: {response.error}")
                        await asyncio.sleep(60) # Tunggu sebelum mencoba lagi jika ada error DB
                        continue 
                    
                    notifications_data = response.data
                    if notifications_data is None:
                        logger.warning("NotificationWorker: Fetched notifications data is None. Assuming empty list. Response: %s", response)
                        notifications_data = []

                    logger.info(f"NotificationWorker: Found {len(notifications_data)} unsent notification records.")
                    
                    if not notifications_data:
                        logger.info("NotificationWorker: No pending notifications to process in this cycle.")

                    for item in notifications_data:
                        notification_id = item.get('id')
                        phone_number = item.get('phone_number')
                        task_details = item.get('tasks') # Ini adalah objek task, bukan list
                        notify_times_list = item.get('notification_times', [])

                        logger.debug(f"NotificationWorker: Processing record ID: {notification_id}, phone: {phone_number}")

                        if not task_details or not task_details.get('id'):
                            logger.warning(f"NotificationWorker: Notification ID {notification_id} has missing or incomplete associated task data. Task data: {task_details}. Skipping.")
                            continue
                        
                        if not notify_times_list:
                            logger.warning(f"NotificationWorker: Notification ID {notification_id} has no notification_times. Skipping.")
                            continue
                        
                        processed_this_record_in_cycle = False
                        for notify_time_str in notify_times_list:
                            if processed_this_record_in_cycle:
                                break # Hanya satu notif per record per siklus worker

                            try:
                                cleaned_time_str = notify_time_str.strip()
                                notify_datetime_utc = datetime.fromisoformat(cleaned_time_str.replace('Z', '+00:00'))
                                logger.debug(f"NotificationWorker: Record ID {notification_id} - Checking notify_time: {cleaned_time_str} (Parsed as UTC: {notify_datetime_utc.isoformat()})")

                                if current_time_utc >= notify_datetime_utc:
                                    logger.info(f"NotificationWorker: CONDITION MET for Notification ID {notification_id}, Task '{task_details.get('name', 'N/A')}', Trigger Time: {cleaned_time_str}")
                                    
                                    task_name = task_details.get('name', 'Tugas Tidak Diketahui')
                                    task_desc = task_details.get('description', 'Tidak ada deskripsi.')
                                    task_jenis = task_details.get('jenis_tugas', 'N/A').capitalize()
                                    task_due_iso = task_details.get('due_date')

                                    if not task_due_iso:
                                        logger.error(f"NotificationWorker: Task '{task_name}' (ID: {task_details.get('id')}) for Notif ID {notification_id} is missing 'due_date'. Cannot format message.")
                                        continue

                                    task_due_utc = datetime.fromisoformat(task_due_iso.replace('Z', '+00:00'))
                                    task_due_wib = task_due_utc.astimezone(INDONESIA_TZ_FOR_WORKER)
                                    deadline_display_wib = task_due_wib.strftime('%d/%m/%Y %H:%M WIB')

                                    # Tentukan jenis pesan berdasarkan seberapa jauh waktu notifikasi (notify_datetime_utc) dari deadline tugas (task_due_utc)
                                    time_from_trigger_to_deadline = task_due_utc - notify_datetime_utc
                                    message_to_send = ""
                                    
                                    # Toleransi 5 menit (300 detik) untuk perbandingan waktu
                                    if abs(time_from_trigger_to_deadline.total_seconds() - 3*24*3600) < 300: # Sekitar 3 hari
                                        message_to_send = (
                                            f"🔔 *Reminder Tugas H-3!*\n\n"
                                            f"📝 *Tugas:* {task_name}\n📖 *Deskripsi:* {task_desc}\n"
                                            f"⏰ *Deadline:* {deadline_display_wib}\n📂 *Jenis:* {task_jenis}\n\n"
                                            "Hai, udah H-3 nih! Jangan lupa untuk menyelesaikan tugas ini ya! 🎯"
                                        )
                                    elif abs(time_from_trigger_to_deadline.total_seconds() - 1*24*3600) < 300: # Sekitar 1 hari
                                        message_to_send = (
                                            f"🔔 *Reminder Tugas H-1 Hari!*\n\n"
                                            f"📝 *Tugas:* {task_name}\n📖 *Deskripsi:* {task_desc}\n"
                                            f"⏰ *Deadline:* {deadline_display_wib}\n📂 *Jenis:* {task_jenis}\n\n"
                                            "Jgn lupa ya, H-1 Hari terakhir! 🚨"
                                        )
                                    elif abs(time_from_trigger_to_deadline.total_seconds() - 1*3600) < 300: # Sekitar 1 jam
                                        message_to_send = (
                                            f"🔔 *Reminder Tugas H-1 Jam!*\n\n"
                                            f"📝 *Tugas:* {task_name}\n📖 *Deskripsi:* {task_desc}\n"
                                            f"⏰ *Deadline:* {deadline_display_wib}\n📂 *Jenis:* {task_jenis}\n\n"
                                            "Gimana udah diupload? Jgn sampe terlambat! ⚡"
                                        )
                                    else:
                                        logger.warning(f"NotificationWorker: Notif ID {notification_id}, Task '{task_name}'. Time diff from deadline ({time_from_trigger_to_deadline}) doesn't match H-3D/1D/1H slots. Sending generic reminder.")
                                        message_to_send = (
                                            f"🔔 *Reminder Tugas!*\n\n"
                                            f"📝 *Tugas:* {task_name}\n⏰ *Deadline:* {deadline_display_wib}\n"
                                            "Segera selesaikan tugasmu!"
                                        )
                                    
                                    logger.info(f"NotificationWorker: Attempting to send to {phone_number} for task '{task_name}' (Notif ID {notification_id})")
                                    await self.bot.send_message(phone_number, message_to_send)
                                    logger.info(f"NotificationWorker: Message sent successfully for Notif ID {notification_id}.")
                                    
                                    update_resp = supabase.table('notifications') \
                                        .update({'is_sent': True}) \
                                        .eq('id', notification_id) \
                                        .execute()
                                    if hasattr(update_resp, 'error') and update_resp.error:
                                         logger.error(f"NotificationWorker: Failed to mark Notif ID {notification_id} as sent. Error: {update_resp.error}")
                                    else:
                                        logger.info(f"NotificationWorker: Successfully marked Notif ID {notification_id} as sent.")
                                    processed_this_record_in_cycle = True 
                                    # break # Hapus break ini jika ingin semua `notify_time` yang cocok dalam satu record ditandai.
                                            # Dengan `processed_this_record_in_cycle`, hanya satu pesan yang dikirim, lalu record ditandai `is_sent`.
                                            # Ini perilaku yang benar: satu picu, kirim, tandai.

                            except ValueError as ve_parse:
                                logger.error(f"NotificationWorker: ValueError parsing time '{notify_time_str}' for Notif ID {notification_id}: {ve_parse}", exc_info=True)
                            except Exception as e_inner_time_loop:
                                logger.error(f"NotificationWorker: Error processing time '{notify_time_str}' for Notif ID {notification_id}: {e_inner_time_loop}", exc_info=True)
                        
                        # Akhir loop untuk setiap notify_time_str dalam satu record notifikasi
                    # Akhir loop untuk setiap item notifikasi

                    # Sleep sebelum siklus berikutnya
                    sleep_duration = 60 # Detik
                    logger.debug(f"NotificationWorker: Cycle finished. Sleeping for {sleep_duration} seconds.")
                    await asyncio.sleep(sleep_duration)
                    
                except Exception as e_main_loop_try:
                    logger.error(f"NotificationWorker: Error in main try block of worker cycle: {e_main_loop_try}", exc_info=True)
                    await asyncio.sleep(60) # Tunggu lebih lama jika ada error di siklus utama

        except ImportError as e_imp: # Menangkap error impor yang mungkin terjadi saat _run benar-benar dieksekusi
            logger.critical(f"NotificationWorker._run: CRITICAL IMPORT ERROR in _run task: {e_imp}", exc_info=True)
        except Exception as e_very_outer:
            logger.critical(f"NotificationWorker._run: CRITICAL UNHANDLED EXCEPTION in _run task: {e_very_outer}", exc_info=True)
        finally:
            logger.info("NotificationWorker._run: Method exiting. self.running is %s", self.running)