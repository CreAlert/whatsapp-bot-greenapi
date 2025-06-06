# src/workers/notification_worker.py
import asyncio
from datetime import datetime
import logging

# Impor Supabase client dari config (pastikan path ini benar!)
# Jika config.py ada di src/, dan file ini di src/workers/, maka ..config sudah benar
SUPABASE_CLIENT_AVAILABLE = False
supabase = None
try:
    from ..config import supabase
    SUPABASE_CLIENT_AVAILABLE = supabase is not None
except ImportError as e:
    logging.getLogger(__name__).error(f"Failed to import supabase from ..config: {e}", exc_info=True)
    # supabase akan tetap None, SUPABASE_CLIENT_AVAILABLE akan False

# Setup logger untuk modul ini
logger = logging.getLogger(__name__)
print(f"### PYPRINT ### notification_worker.py: Module loaded. Logger name: {logger.name}")
logger.info("NotificationWorker module: Logger configured.")

# Definisikan timezone object di level modul
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

logger.info("NotificationWorker module: Supabase client imported/configured check: supabase is not None -> %s", SUPABASE_CLIENT_AVAILABLE)

class NotificationWorker:
    def __init__(self, bot):
        self.bot = bot
        self.running = False
        self.task = None
        print(f"### PYPRINT ### NotificationWorker __init__ called.")
        logger.info("NotificationWorker class: Instance initialized.")

    async def start(self):
        if self.running:
            print("### PYPRINT ### NotificationWorker.start: Worker already running.")
            logger.info("NotificationWorker.start: Worker already running.")
            return self.task
        
        self.running = True
        print("### PYPRINT ### NotificationWorker.start: self.running set to True. Attempting to create _run task.")
        logger.info("NotificationWorker.start: Worker flag set to running. Attempting to create _run task.")
        try:
            self.task = asyncio.create_task(self._run())
            print(f"### PYPRINT ### NotificationWorker.start: asyncio.create_task(self._run) SUCCEEDED. Task: {self.task}")
            logger.info(f"NotificationWorker.start: asyncio.create_task(self._run()) called successfully. Task: {self.task}")
        except Exception as e_create_task:
            print(f"### PYPRINT ERROR ### NotificationWorker.start: FAILED to create_task for _run: {e_create_task}")
            logger.error(f"NotificationWorker.start: FAILED to create_task for _run: {e_create_task}", exc_info=True)
            self.running = False
            self.task = None
        return self.task

    async def stop(self):
        print("### PYPRINT ### NotificationWorker.stop called.")
        logger.info("NotificationWorker.stop: Attempting to stop worker.")
        self.running = False
        if self.task and not self.task.done():
            print(f"### PYPRINT ### NotificationWorker.stop: Task {self.task} found, cancelling.")
            logger.info("NotificationWorker.stop: Cancelling worker task.")
            self.task.cancel()
            try:
                await self.task
                print("### PYPRINT ### NotificationWorker.stop: Task awaited after cancel.")
                logger.info("NotificationWorker.stop: Worker task awaited after cancellation.")
            except asyncio.CancelledError:
                print("### PYPRINT ### NotificationWorker.stop: Task successfully cancelled (Caught CancelledError).")
                logger.info("NotificationWorker.stop: Worker task successfully cancelled and caught CancelledError.")
            except Exception as e:
                print(f"### PYPRINT ERROR ### NotificationWorker.stop: Error awaiting cancelled task: {e}")
                logger.error(f"NotificationWorker.stop: Error encountered while awaiting cancelled task: {e}", exc_info=True)
        elif self.task and self.task.done():
            print(f"### PYPRINT ### NotificationWorker.stop: Task {self.task} was already done.")
            logger.info("NotificationWorker.stop: Worker task was already done.")
        else:
            print("### PYPRINT ### NotificationWorker.stop: No active task to cancel or task is None.")
            logger.info("NotificationWorker.stop: No active task to cancel or task is None.")
        self.task = None
        print("### PYPRINT ### NotificationWorker.stop: Worker fully stopped.")
        logger.info("NotificationWorker.stop: Worker stopped procedure complete.")

    async def _run(self):
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"### PYPRINT _RUN ### NotificationWorker._run: Method entered. self.running is {self.running}")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        logger.info("NotificationWorker._run: Method entered. self.running is %s", self.running)
        
        loop_for_executor = None  # Akan diisi nanti

        try:
            if not SUPABASE_CLIENT_AVAILABLE:
                logger.critical("NotificationWorker._run: Supabase client is NOT AVAILABLE. Worker cannot function. Exiting _run.")
                self.running = False
                return

            logger.info(f"NotificationWorker._run: Timezone objects successfully accessed - UTC: {UTC_TZ_FOR_WORKER}, WIB: {INDONESIA_TZ_FOR_WORKER}")
            logger.info(f"NotificationWorker._run: Supabase client appears accessible (imported successfully).")
            
            loop_for_executor = asyncio.get_event_loop()  # Dapatkan event loop saat ini

            cycle_count = 0
            while self.running:
                cycle_count += 1
                current_time_utc = datetime.now(UTC_TZ_FOR_WORKER)
                print(f"### PYPRINT _RUN ### Cycle {cycle_count}. Current UTC: {current_time_utc.isoformat()}")
                logger.info(f"NotificationWorker: Cycle {cycle_count} START. Current UTC: {current_time_utc.isoformat()}. self.running: {self.running}")
                
                try:
                    logger.debug("NotificationWorker: Fetching unsent notifications from database...")
                    # Jalankan operasi blocking Supabase di executor
                    response = await loop_for_executor.run_in_executor(
                        None,
                        lambda: supabase.table('notifications')
                            .select('id, phone_number, notification_time, reminder_type, task_id, tasks(id, name, description, due_date, jenis_tugas)')
                            .eq('is_sent', False)
                            .execute()
                    )
                    
                    if hasattr(response, 'error') and response.error:
                        logger.error(f"NotificationWorker: Supabase error fetching notifications in cycle {cycle_count}: {response.error}")
                        logger.info(f"NotificationWorker: Cycle {cycle_count} will sleep for 60s due to Supabase fetch error and then continue.")
                        await asyncio.sleep(60)
                        continue
                    
                    notifications_data = response.data
                    if notifications_data is None:
                        logger.warning(f"NotificationWorker: Fetched notifications data is None in cycle {cycle_count}. Assuming empty. Response: {response}")
                        notifications_data = []

                    logger.info(f"NotificationWorker: Found {len(notifications_data)} unsent notification records in cycle {cycle_count}.")
                    
                    if not notifications_data:
                        logger.info(f"NotificationWorker: No pending notifications to process in this cycle {cycle_count}.")

                    for item_index, item in enumerate(notifications_data):
                        notification_id = item.get('id')
                        phone_number = item.get('phone_number')
                        task_details = item.get('tasks')
                        notify_time_str = item.get('notification_time')
                        reminder_type = item.get('reminder_type', 'N/A')

                        logger.info(f"NotificationWorker: Cycle {cycle_count}, Processing item {item_index + 1}/{len(notifications_data)}, Notif ID: {notification_id}")
                        print(f"### PYPRINT _RUN ### Processing record ID: {notification_id}, phone: {phone_number}, type: {reminder_type}")
                        logger.debug(f"NotificationWorker: Processing record ID: {notification_id}, phone: {phone_number}, type: {reminder_type}")

                        if not task_details or not task_details.get('id'):
                            logger.warning(f"NotificationWorker: Notif ID {notification_id} has missing/incomplete task data. Task: {task_details}. Skipping.")
                            continue
                        
                        if not notify_time_str:
                            logger.warning(f"NotificationWorker: Notif ID {notification_id} has no notification_time. Skipping.")
                            continue

                        try:
                            cleaned_time_str = notify_time_str.strip()
                            notify_datetime_utc = datetime.fromisoformat(cleaned_time_str.replace('Z', '+00:00'))
                            logger.debug(f"NotificationWorker: Record ID {notification_id} - Checking notification_time: {cleaned_time_str} (Parsed UTC: {notify_datetime_utc.isoformat()})")

                            if current_time_utc >= notify_datetime_utc:
                                print(f"### PYPRINT _RUN ### CONDITION MET for Notif ID {notification_id}, Task '{task_details.get('name', 'N/A')}', Type: {reminder_type}")
                                logger.info(f"NotificationWorker: CONDITION MET for Notif ID {notification_id}, Task '{task_details.get('name', 'N/A')}', Type: {reminder_type}")
                                
                                task_name = task_details.get('name', 'Tugas Tidak Diketahui')
                                task_desc = task_details.get('description', 'Tidak ada deskripsi.')
                                task_jenis = task_details.get('jenis_tugas', 'N/A').capitalize()
                                task_due_iso = task_details.get('due_date')

                                if not task_due_iso:
                                    logger.error(f"NotificationWorker: Task '{task_name}' (ID: {task_details.get('id')}) for Notif ID {notification_id} missing 'due_date'.")
                                    continue

                                task_due_utc = datetime.fromisoformat(task_due_iso.replace('Z', '+00:00'))
                                task_due_wib = task_due_utc.astimezone(INDONESIA_TZ_FOR_WORKER)
                                deadline_display_wib = task_due_wib.strftime('%d/%m/%Y %H:%M WIB')
                                
                                # Pesan berdasarkan reminder_type
                                if reminder_type == "H-3D":
                                    message_to_send = (
                                        "🔔 *Hai, udah H-3 nih! Jangan lupa untuk menyelesaikan tugas ini ya!*\n\n"
                                        f"📝 *Tugas:* {task_name}\n"
                                        f"📖 *Deskripsi:* {task_desc}\n"
                                        f"⏰ *Deadline:* {deadline_display_wib}\n"
                                        f"📂 *Jenis:* {task_jenis}"
                                    )
                                elif reminder_type == "H-1D":
                                    message_to_send = (
                                        "🔔 *Jangan lupa ya, udah 24 jam terakhir!*\n\n"
                                        f"📝 *Tugas:* {task_name}\n"
                                        f"📖 *Deskripsi:* {task_desc}\n"
                                        f"⏰ *Deadline:* {deadline_display_wib}\n"
                                        f"📂 *Jenis:* {task_jenis}"
                                    )
                                elif reminder_type == "H-1H":
                                    message_to_send = (
                                        "🔔 *Gimana udah diupload? Jangan sampe terlambat!*\n\n"
                                        f"📝 *Tugas:* {task_name}\n"
                                        f"📖 *Deskripsi:* {task_desc}\n"
                                        f"⏰ *Deadline:* {deadline_display_wib}\n"
                                        f"📂 *Jenis:* {task_jenis}"
                                    )
                                else:
                                    logger.warning(f"NotificationWorker: Unknown reminder_type '{reminder_type}' for Notif ID {notification_id}. Sending generic reminder.")
                                    message_to_send = (
                                        "🔔 *Reminder Tugas!*\n\n"
                                        f"📝 *Tugas:* {task_name}\n"
                                        f"⏰ *Deadline:* {deadline_display_wib}\n"
                                        "Segera selesaikan tugasmu!"
                                    )
                                
                                print(f"### PYPRINT _RUN ### Attempting send to {phone_number} for task '{task_name}' with message: '{message_to_send[:30]}...'")
                                logger.info(f"NotificationWorker: Attempting send to {phone_number} for task '{task_name}' (Notif ID {notification_id}, Type: {reminder_type})")
                                
                                send_response = await loop_for_executor.run_in_executor(
                                    None,
                                    lambda: self.bot.api.sending.sendMessage(chatId=phone_number, message=message_to_send)
                                )
                                
                                logger.info(f"NotificationWorker: sendMessage API call completed. Response: {send_response}")
                                
                                update_db_response = await loop_for_executor.run_in_executor(
                                    None,
                                    lambda: supabase.table('notifications')
                                        .update({'is_sent': True})
                                        .eq('id', notification_id)
                                        .execute()
                                )
                                if hasattr(update_db_response, 'error') and update_db_response.error:
                                    logger.error(f"NotificationWorker: Failed to mark Notif ID {notification_id} as sent. Error: {update_db_response.error}")
                                else:
                                    logger.info(f"NotificationWorker: Successfully marked Notif ID {notification_id} as sent.")
                            else:
                                logger.debug(f"NotificationWorker: Notif ID {notification_id} time not yet reached. Current: {current_time_utc.isoformat()}, Notify: {notify_datetime_utc.isoformat()}")
                        except ValueError as ve_parse:
                            logger.error(f"NotificationWorker: ValueError parsing time '{notify_time_str}' for Notif ID {notification_id}: {ve_parse}", exc_info=True)
                        except Exception as e_inner:
                            logger.error(f"NotificationWorker: Error processing notification ID {notification_id}: {e_inner}", exc_info=True)
                    
                    logger.info(f"NotificationWorker: Finished processing all items (if any) in cycle {cycle_count}.")
                    sleep_duration = 30
                    print(f"### PYPRINT _RUN ### Cycle {cycle_count} finished. Sleeping {sleep_duration}s.")
                    logger.info(f"NotificationWorker: Cycle {cycle_count} COMPLETED successfully. Preparing to sleep for {sleep_duration}s.")
                    await asyncio.sleep(sleep_duration)
                    logger.info(f"NotificationWorker: Cycle {cycle_count} AWAKENED after {sleep_duration}s sleep.")
                    
                except Exception as e_main_loop_try:
                    logger.error(f"NotificationWorker: Uncaught error in main processing block of worker cycle {cycle_count}: {e_main_loop_try}", exc_info=True)
                    logger.info(f"NotificationWorker: Cycle {cycle_count} will sleep for 60s due to unhandled error in processing block and then continue.")
                    await asyncio.sleep(60)
                    continue

            logger.info(f"NotificationWorker._run: Gracefully exited 'while self.running' loop. self.running is {self.running}. Total cycles: {cycle_count}.")

        except ImportError as e_imp:
            print(f"### PYPRINT _RUN ERROR ### CRITICAL IMPORT ERROR in _run task: {e_imp}")
            logger.critical(f"NotificationWorker._run: CRITICAL IMPORT ERROR in _run task: {e_imp}", exc_info=True)
            self.running = False
        except Exception as e_very_outer:
            print(f"### PYPRINT _RUN ERROR ### CRITICAL UNHANDLED EXCEPTION in _run task: {e_very_outer}")
            logger.critical(f"NotificationWorker._run: CRITICAL UNHANDLED EXCEPTION in _run task (outside main while loop): {e_very_outer}", exc_info=True)
            self.running = False
        finally:
            print(f"### PYPRINT _RUN ### Method _run FINALLY block. self.running is {self.running}")
            task_status = "No task object or self.task not set"
            if hasattr(self, 'task') and self.task:
                task_is_done = self.task.done()
                task_is_cancelled = self.task.cancelled()
                task_exception_info = "N/A"
                if task_is_done and not task_is_cancelled:
                    try:
                        exception = self.task.exception()
                        if exception:
                            task_exception_info = str(exception)
                        else:
                            task_exception_info = "No exception"
                    except asyncio.InvalidStateError:
                        task_exception_info = "InvalidStateError (task not truly done?)"
                
                task_status = (f"Task Name: {self.task.get_name()}, Done: {task_is_done}, "
                               f"Cancelled: {task_is_cancelled}, Exception: {task_exception_info}")

            logger.info(f"NotificationWorker._run: FINALLY block reached. self.running is {self.running}. Status of this worker's task: {task_status}")
            logger.info("NotificationWorker._run: Method exiting. self.running is %s", self.running)