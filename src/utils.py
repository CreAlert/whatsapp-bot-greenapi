from datetime import datetime, timedelta
from typing import List, Dict
from .config import supabase, States

def update_state_with_history(notification, new_state: str) -> None:
    """Update state while preserving previous states in history"""
    current_state = notification.state_manager.get_state(notification.sender)
    state_data = notification.state_manager.get_state_data(notification.sender) or {}
    
    # Initialize history if not exists
    if "state_history" not in state_data:
        state_data["state_history"] = []
    
    # Add current state to history before changing
    if current_state:
        state_data["state_history"].append(current_state)
    
    # Update state and data
    notification.state_manager.update_state_data(notification.sender, state_data)
    notification.state_manager.update_state(notification.sender, new_state)

async def get_tasks(class_name: str, day_name: str) -> List[Dict]:
    """Get tasks from Supabase"""
    try:
        response = supabase.table('tasks') \
            .select('*') \
            .eq('class', class_name) \
            .eq('day', day_name) \
            .order('due_date') \
            .execute()
        return response.data
    except Exception as e:
        return []

async def save_notification(phone: str, task_id: int, notify_times: List[str]):
    """Save notification to Supabase"""
    try:
        # Create notification record with all times in one record
        notification = {
            "phone_number": phone,
            "task_id": task_id,
            "notification_times": notify_times,
            "is_sent": False
        }
        
        # Insert notification
        response = supabase.table('notifications') \
            .insert(notification) \
            .execute()
        
        if response.data:
            print(f"Successfully saved notifications for task {task_id} at times: {notify_times}")
            return response.data
        else:
            print(f"Failed to save notifications for task {task_id}")
            return None
    except Exception as e:
        print(f"Error saving notifications: {e}")
        return None

def calculate_notification_times(due_date: datetime) -> List[str]:
    """Calculate notification times for a task"""
    return [
        (due_date - timedelta(days=7)).isoformat(),
        (due_date - timedelta(days=3)).isoformat(),
        (due_date - timedelta(days=1)).isoformat(),
        (due_date - timedelta(hours=12)).isoformat(),
        (due_date - timedelta(hours=3)).isoformat()
    ] 