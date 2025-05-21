import asyncio
from datetime import datetime
import logging
from typing import List, Dict
from ..config import supabase
from whatsapp_chatbot_python import GreenAPIBot

logger = logging.getLogger(__name__)

class NotificationWorker:
    def __init__(self, bot):
        self.bot = bot
        self.running = False
        self.task = None

    async def start(self):
        """Start the notification worker"""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run())
        return self.task

    async def stop(self):
        """Stop the notification worker"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

    async def _run(self):
        """Main worker loop"""
        while self.running:
            try:
                # Get all unsent notifications
                response = supabase.table('notifications') \
                    .select('*, tasks(*)') \
                    .eq('is_sent', False) \
                    .execute()
                
                notifications = response.data
                
                for notification in notifications:
                    try:
                        # Get notification times
                        notify_times = notification.get('notification_times', [])
                        if not notify_times:
                            continue
                        
                        # Get task data
                        task = notification.get('tasks', {})
                        if not task:
                            continue
                        
                        # Check each notification time
                        current_time = datetime.now()
                        for notify_time in notify_times:
                            notify_datetime = datetime.fromisoformat(notify_time.replace('Z', '+00:00'))
                            
                            # If it's time to send notification
                            if current_time >= notify_datetime:
                                # Calculate time difference
                                time_diff = notify_datetime - current_time
                                days_diff = time_diff.days
                                hours_diff = time_diff.seconds // 3600

                                # Create different messages based on time difference
                                if days_diff == 3:
                                    message = (
                                        "🔔 *Reminder Tugas!*\n\n"
                                        f"📝 *Tugas:* {task['name']}\n"
                                        f"📖 *Deskripsi:* {task['description']}\n"
                                        f"⏰ *Deadline:* {notify_datetime.strftime('%d/%m/%Y %H:%M')}\n"
                                        f"📂 *Jenis:* {task['jenis_tugas'].capitalize()}\n\n"
                                        "Hai, udah H-3 nih! Jangan lupa untuk menyelesaikan tugas ini ya! 🎯"
                                    )
                                elif days_diff == 1:
                                    message = (
                                        "🔔 *Reminder Tugas!*\n\n"
                                        f"📝 *Tugas:* {task['name']}\n"
                                        f"📖 *Deskripsi:* {task['description']}\n"
                                        f"⏰ *Deadline:* {notify_datetime.strftime('%d/%m/%Y %H:%M')}\n"
                                        f"📂 *Jenis:* {task['jenis_tugas'].capitalize()}\n\n"
                                        "Jgn lupa ya, udah 24 jam terakhir! 🚨"
                                    )
                                elif hours_diff == 1:
                                    message = (
                                        "🔔 *Reminder Tugas!*\n\n"
                                        f"📝 *Tugas:* {task['name']}\n"
                                        f"📖 *Deskripsi:* {task['description']}\n"
                                        f"⏰ *Deadline:* {notify_datetime.strftime('%d/%m/%Y %H:%M')}\n"
                                        f"📂 *Jenis:* {task['jenis_tugas'].capitalize()}\n\n"
                                        "Gimana udah diupload? Jgn sampe terlambat! ⚡"
                                    )
                                
                                await self.bot.send_message(
                                    notification['phone_number'],
                                    message
                                )
                                
                                # Mark notification as sent
                                supabase.table('notifications') \
                                    .update({'is_sent': True}) \
                                    .eq('id', notification['id']) \
                                    .execute()
                    
                    except Exception as e:
                        print(f"Error processing notification: {e}")
                        continue
                
                # Sleep for 60 seconds before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                print(f"Error in notification worker: {e}")
                # Sleep for 60 seconds on error
                await asyncio.sleep(60) 