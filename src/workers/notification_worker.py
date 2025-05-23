import asyncio
from datetime import datetime
import logging
from typing import List, Dict
from ..config import supabase
from whatsapp_chatbot_python import GreenAPIBot

# Definisikan timezone object di level modul agar pasti tersedia
try:
    from zoneinfo import ZoneInfo
    UTC_TZ_FOR_WORKER = ZoneInfo("UTC")
    INDONESIA_TZ_FOR_WORKER = ZoneInfo("Asia/Jakarta")
except ImportError:
    import pytz
    UTC_TZ_FOR_WORKER = pytz.utc
    INDONESIA_TZ_FOR_WORKER = pytz.timezone("Asia/Jakarta")

logger = logging.getLogger(__name__)

class NotificationWorker:
    def __init__(self, bot):
        self.bot = bot
        self.running = False
        self.task = None
        logger.info("NotificationWorker initialized")

    async def start(self):
        """Start the notification worker"""
        if self.running:
            logger.info("NotificationWorker.start: Worker already running.")
            return
        
        self.running = True
        logger.info("NotificationWorker.start: Worker starting and creating task for _run.")
        self.task = asyncio.create_task(self._run())
        return self.task

    async def stop(self):
        """Stop the notification worker"""
        logger.info("NotificationWorker.stop: Attempting to stop worker.")
        self.running = False
        if self.task:
            logger.info("NotificationWorker.stop: Cancelling worker task.")
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                logger.info("NotificationWorker.stop: Worker task successfully cancelled.")
            except Exception as e:
                logger.error(f"NotificationWorker.stop: Error encountered while awaiting cancelled task: {e}", exc_info=True)
            self.task = None
        logger.info("NotificationWorker.stop: Worker stopped.")

    async def _run(self):
        """Main worker loop"""
        # Log paling atas untuk memastikan metode ini dimasuki
        logger.info("NotificationWorker._run: Method entered. self.running is %s", self.running)
        
        try:
            # Pastikan timezone object sudah terdefinisi dan bisa diakses
            logger.info(f"NotificationWorker._run: Timezone objects successfully accessed - UTC: {UTC_TZ_FOR_WORKER}, WIB: {INDONESIA_TZ_FOR_WORKER}")
            
            # Pastikan supabase client bisa diakses
            logger.info(f"NotificationWorker._run: Supabase client accessible: {supabase is not None}")
            
            while self.running:
                current_time_utc = datetime.now(UTC_TZ_FOR_WORKER)
                logger.info(f"NotificationWorker: New cycle starting. Current UTC time: {current_time_utc.isoformat()}")
                
                try:
                    # Get all unsent notifications
                    logger.debug("NotificationWorker: Fetching unsent notifications from database...")
                    response = supabase.table('notifications') \
                        .select('*, tasks(*)') \
                        .eq('is_sent', False) \
                        .execute()
                    
                    notifications = response.data
                    logger.info(f"NotificationWorker: Found {len(notifications)} unsent notifications")
                    
                    for notification in notifications:
                        try:
                            # Get notification times
                            notify_times = notification.get('notification_times', [])
                            if not notify_times:
                                logger.warning(f"NotificationWorker: Notification {notification.get('id')} has no notification times")
                                continue
                            
                            # Get task data
                            task = notification.get('tasks', {})
                            if not task:
                                logger.warning(f"NotificationWorker: Notification {notification.get('id')} has no associated task")
                                continue
                            
                            logger.debug(f"NotificationWorker: Processing notification {notification.get('id')} for task {task.get('name')}")
                            
                            # Check each notification time
                            for notify_time in notify_times:
                                notify_datetime_utc = datetime.fromisoformat(notify_time.replace('Z', '+00:00'))
                                
                                # If it's time to send notification
                                if current_time_utc >= notify_datetime_utc:
                                    logger.info(f"NotificationWorker: Sending notification for task {task.get('name')} at {current_time_utc.isoformat()}")
                                    
                                    # Get task deadline in WIB for display
                                    task_due_date_utc = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                                    task_due_date_wib = task_due_date_utc.astimezone(INDONESIA_TZ_FOR_WORKER)
                                    deadline_display = task_due_date_wib.strftime('%d/%m/%Y %H:%M WIB')
                                    
                                    # Calculate time difference in UTC
                                    time_diff = task_due_date_utc - notify_datetime_utc
                                    days_diff = time_diff.days
                                    hours_diff = time_diff.seconds // 3600

                                    # Create different messages based on time difference
                                    if days_diff == 3:
                                        message = (
                                            "🔔 *Reminder Tugas!*\n\n"
                                            f"📝 *Tugas:* {task['name']}\n"
                                            f"📖 *Deskripsi:* {task['description']}\n"
                                            f"⏰ *Deadline:* {deadline_display}\n"
                                            f"📂 *Jenis:* {task['jenis_tugas'].capitalize()}\n\n"
                                            "Hai, udah H-3 nih! Jangan lupa untuk menyelesaikan tugas ini ya! 🎯"
                                        )
                                    elif days_diff == 1:
                                        message = (
                                            "🔔 *Reminder Tugas!*\n\n"
                                            f"📝 *Tugas:* {task['name']}\n"
                                            f"📖 *Deskripsi:* {task['description']}\n"
                                            f"⏰ *Deadline:* {deadline_display}\n"
                                            f"📂 *Jenis:* {task['jenis_tugas'].capitalize()}\n\n"
                                            "Jgn lupa ya, udah 24 jam terakhir! 🚨"
                                        )
                                    elif hours_diff == 1:
                                        message = (
                                            "🔔 *Reminder Tugas!*\n\n"
                                            f"📝 *Tugas:* {task['name']}\n"
                                            f"📖 *Deskripsi:* {task['description']}\n"
                                            f"⏰ *Deadline:* {deadline_display}\n"
                                            f"📂 *Jenis:* {task['jenis_tugas'].capitalize()}\n\n"
                                            "Gimana udah diupload? Jgn sampe terlambat! ⚡"
                                        )
                                    
                                    await self.bot.send_message(
                                        notification['phone_number'],
                                        message
                                    )
                                    
                                    # Mark notification as sent
                                    logger.info(f"NotificationWorker: Marking notification {notification.get('id')} as sent")
                                    supabase.table('notifications') \
                                        .update({'is_sent': True}) \
                                        .eq('id', notification['id']) \
                                        .execute()
                        
                        except Exception as e:
                            logger.error(f"NotificationWorker: Error processing notification {notification.get('id')}: {e}", exc_info=True)
                            continue
                    
                    # Sleep for 60 seconds before next check
                    logger.debug("NotificationWorker: Sleeping for 60 seconds before next cycle")
                    await asyncio.sleep(60)
                    
                except Exception as e_inner_loop:
                    # Tangkap error spesifik dari logika pemrosesan notifikasi
                    logger.error(f"NotificationWorker: Error during notification processing in while loop: {e_inner_loop}", exc_info=True)
                    # Sleep for 60 seconds on error
                    await asyncio.sleep(60)

        except Exception as e_very_outer:
            # Tangkap error apapun yang mungkin terjadi di luar loop utama _run
            logger.critical(f"NotificationWorker._run: CRITICAL UNHANDLED EXCEPTION in _run task: {e_very_outer}", exc_info=True)
        finally:
            # Log ini akan muncul jika loop `while self.running` selesai
            # atau jika ada exception yang menyebabkan keluar dari blok try utama di _run
            logger.info("NotificationWorker._run: Method exiting. self.running is %s", self.running) 