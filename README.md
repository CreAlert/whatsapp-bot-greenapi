# CreAlert - Academic Task Management Bot 🚀
**Kolaborasi dengan Pendidikan Vokasi Program Studi Bisnis Kreatif Universitas Indonesia**

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-4DAF7C)](LICENSE)
![Vokasi UI](https://img.shields.io/badge/Partner-Vokasi%20UI%20Bisnis%20Kreatif-FF6F00)

> WhatsApp bot pengelola tugas akademik berbasis kreativitas dan inovasi, dikembangkan sebagai bagian dari ekosistem digital Pendidikan Vokasi Program Studi Bisnis Kreatif UI 

## 💡 Key Features

#### ✅ View task list by class and day
Easily check what’s due and when – tasks are neatly organized by class and day, so you’ll never miss a beat.

#### ⏰ Set reminders for assignment deadlines
Stay ahead of your deadlines – customize your own reminder schedule and let Crealert do the rest.

#### 🔔 Get automatic alerts before assignments are due
Don’t worry about forgetting! We’ll remind you at D-7, D-3, D-1, 12 hours, and 3 hours before your assignment is due.

#### 🛠️ Admin menu to add new tasks
Got new assignments to share? Use the admin menu to easily add and manage tasks for your class.

## 🚀 Tech Stack

### Core Components
- **Backend**: Python 3.9+ (AsyncIO)
- **Messaging**: GreenAPI WhatsApp Gateway
- **Database**: Supabase (PostgreSQL 14)
- **Task Queue**: Redis + RQ (for notifications)

### Key Libraries
```python
whatsapp_chatbot_python==1.4.2
supabase==2.3.1                 
python-dotenv==1.0.0            
apscheduler==3.9.1 
```

## ⚙️ Setup

1. Clone repo

``` bash
git clone https://github.com/CreAlert/whatsapp-bot-greenapi.git
```

2. Configure environment

```bash
cp .env.example .env
# Fill in your credentials
```

3.  Run the system

```bash
# Start main bot
python -m bot.py
```

## 🔢 Environment Variables

- `GREENAPI_ID`: GreenAPI ID
- `GREENAPI_TOKEN`: GreenAPI Token
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase API key
- `ADMIN_PHONES`: Admin phone number list

## 📄 License
MIT © 2025 Program Studi Bisnis Kreatif - Pendidikan Vokasi Universitas Indonesia
