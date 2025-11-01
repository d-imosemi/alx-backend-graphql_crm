# 🧩 CRM Project — Task Queue & Caching Setup

This document provides the setup steps for running the **CRM project** with **Redis**, **Celery**, and **Django** integration.

---

## 🚀 1. Install Dependencies

Ensure you have Python and Redis installed.

### 🔹 Install Redis

#### On macOS (using Homebrew):
```bash
brew install redis
brew services start redis


sudo apt update
sudo apt install redis-server -y
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Verify Redis is running:

redis-cli ping
# Expected output: PONG

pip install -r requirements.txt


⚙️ 2. Run Migrations

python manage.py migrate


🧠 3. Start Celery Worker
celery -A crm worker -l info


⏰ 4. Start Celery Beat (Scheduler)
celery -A crm beat -l info


🪵 5. Verify Logs
/tmp/crm_report_log.txt


# You can inspect logs using:
tail -f /tmp/crm_report_log.txt

# Stop all Celery processes:

pkill -f 'celery'

# Restart Redis:

sudo systemctl restart redis-server


# Clear Redis cache:
redis-cli FLUSHALL
