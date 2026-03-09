import logging
import json
import uuid
from datetime import datetime, timedelta
from livekit.agents import function_tool, RunContext
import requests
from langchain_community.tools import DuckDuckGoSearchRun
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

# --- Local JSON storage helpers ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")
REMINDERS_FILE = os.path.join(DATA_DIR, "reminders.json")
EVENTS_FILE = os.path.join(DATA_DIR, "events.json")


def _load_json(path: str) -> list:
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []


def _save_json(path: str, data: list):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)

MEMORIES_FILE = os.path.join(DATA_DIR, "memories.json")

@function_tool()
async def get_weather(
    context: RunContext,  # type: ignore
    city: str) -> str:
    """
    Get the current weather for a given city.
    """
    try:
        response = requests.get(
            f"https://wttr.in/{city}?format=3")
        if response.status_code == 200:
            logging.info(f"Weather for {city}: {response.text.strip()}")
            return response.text.strip()   
        else:
            logging.error(f"Failed to get weather for {city}: {response.status_code}")
            return f"Could not retrieve weather for {city}."
    except Exception as e:
        logging.error(f"Error retrieving weather for {city}: {e}")
        return f"An error occurred while retrieving weather for {city}." 

@function_tool()
async def search_web(
    context: RunContext,  # type: ignore
    query: str) -> str:
    """
    Search the web using DuckDuckGo.
    """
    try:
        results = DuckDuckGoSearchRun().run(tool_input=query)
        logging.info(f"Search results for '{query}': {results}")
        return results
    except Exception as e:
        logging.error(f"Error searching the web for '{query}': {e}")
        return f"An error occurred while searching the web for '{query}'."    

@function_tool()    
async def send_email(
    context: RunContext,  # type: ignore
    to_email: str,
    subject: str,
    message: str,
    cc_email: Optional[str] = None
) -> str:
    """
    Send an email through Gmail.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        message: Email body content
        cc_email: Optional CC email address
    """
    try:
        # Gmail SMTP configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        # Get credentials from environment variables
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")  # Use App Password, not regular password
        
        if not gmail_user or not gmail_password:
            logging.error("Gmail credentials not found in environment variables")
            return "Email sending failed: Gmail credentials not configured."
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add CC if provided
        recipients = [to_email]
        if cc_email:
            msg['Cc'] = cc_email
            recipients.append(cc_email)
        
        # Attach message body
        msg.attach(MIMEText(message, 'plain'))
        
        # Connect to Gmail SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable TLS encryption
        server.login(gmail_user, gmail_password)
        
        # Send email
        text = msg.as_string()
        server.sendmail(gmail_user, recipients, text)
        server.quit()
        
        logging.info(f"Email sent successfully to {to_email}")
        return f"Email sent successfully to {to_email}"
        
    except smtplib.SMTPAuthenticationError:
        logging.error("Gmail authentication failed")
        return "Email sending failed: Authentication error. Please check your Gmail credentials."
    except smtplib.SMTPException as e:
        logging.error(f"SMTP error occurred: {e}")
        return f"Email sending failed: SMTP error - {str(e)}"
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return f"An error occurred while sending email: {str(e)}"

@function_tool()
async def remember(
    context: RunContext,  # type: ignore
    information: str,
    category: Optional[str] = "general",
) -> str:
    """
    Save important information to memory for later recall.
    Use this when the user asks you to remember something, or shares personal
    preferences, facts, schedules, or anything worth remembering.

    Args:
        information: The information to remember.
        category: Category like personal, preference, schedule, contact, or general.
    """
    try:
        memories = _load_json(MEMORIES_FILE)
        new_memory = {
            "id": str(uuid.uuid4())[:8],
            "information": information,
            "category": category,
            "created": datetime.now().isoformat(),
        }
        memories.append(new_memory)
        _save_json(MEMORIES_FILE, memories)
        logging.info(f"Memory saved: {information}")
        return f"I've remembered that: {information}"
    except Exception as e:
        logging.error(f"Error saving memory: {e}")
        return f"I couldn't save that to memory: {str(e)}"


@function_tool()
async def recall(
    context: RunContext,  # type: ignore
    query: str,
) -> str:
    """
    Search memory for previously saved information.
    Use this when the user asks about something they previously told you,
    or when you need context about the user's preferences or past conversations.
    All memories are returned so you can find the most relevant ones.

    Args:
        query: What to search for in memory.
    """
    try:
        memories = _load_json(MEMORIES_FILE)
        if not memories:
            return "I don't have any memories saved yet."

        lines = []
        for m in memories:
            lines.append(f"- [{m['category']}] {m['information']}")
        memory_text = "\n".join(lines)
        return f"Here's everything I remember:\n{memory_text}\n\nThe user is asking about: {query}"
    except Exception as e:
        logging.error(f"Error recalling memory: {e}")
        return f"I couldn't search my memory: {str(e)}"


# ============================================================
# TASK MANAGEMENT
# ============================================================

@function_tool()
async def add_task(
    context: RunContext,  # type: ignore
    task: str,
    priority: Optional[str] = "medium",
) -> str:
    """
    Add a new task to the to-do list.

    Args:
        task: Description of the task.
        priority: Priority level - low, medium, or high. Defaults to medium.
    """
    try:
        tasks = _load_json(TASKS_FILE)
        new_task = {
            "id": str(uuid.uuid4())[:8],
            "task": task,
            "priority": priority,
            "status": "pending",
            "created": datetime.now().isoformat(),
        }
        tasks.append(new_task)
        _save_json(TASKS_FILE, tasks)
        logging.info(f"Task added: {task}")
        return f"Task added: '{task}' with {priority} priority."
    except Exception as e:
        logging.error(f"Error adding task: {e}")
        return f"Failed to add task: {str(e)}"


@function_tool()
async def list_tasks(
    context: RunContext,  # type: ignore
    status: Optional[str] = "pending",
) -> str:
    """
    List tasks from the to-do list.

    Args:
        status: Filter by status - pending, completed, or all. Defaults to pending.
    """
    try:
        tasks = _load_json(TASKS_FILE)
        if status != "all":
            tasks = [t for t in tasks if t["status"] == status]
        if not tasks:
            return f"No {status} tasks found."
        lines = []
        for t in tasks:
            marker = "done" if t["status"] == "completed" else t["priority"]
            lines.append(f"- [{marker}] {t['task']} (id: {t['id']})")
        return f"Tasks ({status}):\n" + "\n".join(lines)
    except Exception as e:
        logging.error(f"Error listing tasks: {e}")
        return f"Failed to list tasks: {str(e)}"


@function_tool()
async def complete_task(
    context: RunContext,  # type: ignore
    task_id: str,
) -> str:
    """
    Mark a task as completed.

    Args:
        task_id: The ID of the task to complete.
    """
    try:
        tasks = _load_json(TASKS_FILE)
        for t in tasks:
            if t["id"] == task_id:
                t["status"] = "completed"
                t["completed_at"] = datetime.now().isoformat()
                _save_json(TASKS_FILE, tasks)
                return f"Task '{t['task']}' marked as completed."
        return f"No task found with id: {task_id}"
    except Exception as e:
        logging.error(f"Error completing task: {e}")
        return f"Failed to complete task: {str(e)}"


@function_tool()
async def delete_task(
    context: RunContext,  # type: ignore
    task_id: str,
) -> str:
    """
    Delete a task from the to-do list.

    Args:
        task_id: The ID of the task to delete.
    """
    try:
        tasks = _load_json(TASKS_FILE)
        original_len = len(tasks)
        tasks = [t for t in tasks if t["id"] != task_id]
        if len(tasks) == original_len:
            return f"No task found with id: {task_id}"
        _save_json(TASKS_FILE, tasks)
        return "Task deleted."
    except Exception as e:
        logging.error(f"Error deleting task: {e}")
        return f"Failed to delete task: {str(e)}"


# ============================================================
# REMINDERS
# ============================================================

def _parse_reminder_time(time_str: str) -> datetime:
    """Parse a time string like '5pm', '17:00', '30 minutes', '2 hours' into a datetime."""
    time_str = time_str.strip().lower()
    now = datetime.now()

    # Relative times: "30 minutes", "2 hours", "1 hour"
    for unit, delta_fn in [("minute", lambda x: timedelta(minutes=x)),
                           ("hour", lambda x: timedelta(hours=x))]:
        if unit in time_str:
            num = int("".join(filter(str.isdigit, time_str)) or "1")
            return now + delta_fn(num)

    # Absolute times: "5pm", "5:30pm", "17:00"
    for fmt in ["%I:%M%p", "%I%p", "%H:%M"]:
        try:
            t = datetime.strptime(time_str, fmt).time()
            result = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
            if result <= now:
                result += timedelta(days=1)
            return result
        except ValueError:
            continue

    # Fallback: treat as minutes
    try:
        num = int(time_str)
        return now + timedelta(minutes=num)
    except ValueError:
        raise ValueError(f"Could not parse time: {time_str}")


@function_tool()
async def set_reminder(
    context: RunContext,  # type: ignore
    reminder: str,
    time: str,
) -> str:
    """
    Set a reminder for a specific time. The agent will notify the user when it's due.

    Args:
        reminder: What to remind the user about.
        time: When to remind. Accepts formats like '5pm', '17:00', '30 minutes', '2 hours'.
    """
    try:
        remind_at = _parse_reminder_time(time)
        reminders = _load_json(REMINDERS_FILE)
        new_reminder = {
            "id": str(uuid.uuid4())[:8],
            "reminder": reminder,
            "remind_at": remind_at.isoformat(),
            "status": "active",
            "created": datetime.now().isoformat(),
        }
        reminders.append(new_reminder)
        _save_json(REMINDERS_FILE, reminders)
        time_display = remind_at.strftime("%I:%M %p")
        logging.info(f"Reminder set: {reminder} at {time_display}")
        return f"Reminder set: '{reminder}' at {time_display}."
    except ValueError as e:
        return str(e)
    except Exception as e:
        logging.error(f"Error setting reminder: {e}")
        return f"Failed to set reminder: {str(e)}"


@function_tool()
async def list_reminders(
    context: RunContext,  # type: ignore
) -> str:
    """
    List all active reminders.
    """
    try:
        reminders = _load_json(REMINDERS_FILE)
        active = [r for r in reminders if r["status"] == "active"]
        if not active:
            return "No active reminders."
        lines = []
        for r in active:
            t = datetime.fromisoformat(r["remind_at"]).strftime("%I:%M %p")
            lines.append(f"- {r['reminder']} at {t} (id: {r['id']})")
        return "Active reminders:\n" + "\n".join(lines)
    except Exception as e:
        logging.error(f"Error listing reminders: {e}")
        return f"Failed to list reminders: {str(e)}"


def check_due_reminders() -> list[dict]:
    """Check for reminders that are due. Returns list of due reminders and marks them as done."""
    try:
        reminders = _load_json(REMINDERS_FILE)
        now = datetime.now()
        due = []
        for r in reminders:
            if r["status"] == "active" and datetime.fromisoformat(r["remind_at"]) <= now:
                r["status"] = "done"
                due.append(r)
        if due:
            _save_json(REMINDERS_FILE, reminders)
        return due
    except Exception:
        return []


# ============================================================
# CALENDAR / EVENTS
# ============================================================

@function_tool()
async def add_event(
    context: RunContext,  # type: ignore
    title: str,
    date: str,
    time: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """
    Add an event to the calendar.

    Args:
        title: Name of the event.
        date: Date of the event in YYYY-MM-DD format, or a day name like 'monday', 'tomorrow'.
        time: Optional time of the event like '3pm', '14:00'.
        description: Optional description or notes for the event.
    """
    try:
        event_date = _parse_event_date(date)
        events = _load_json(EVENTS_FILE)
        new_event = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "date": event_date.isoformat(),
            "time": time,
            "description": description,
            "created": datetime.now().isoformat(),
        }
        events.append(new_event)
        _save_json(EVENTS_FILE, events)
        date_display = event_date.strftime("%A, %B %d, %Y")
        time_display = f" at {time}" if time else ""
        logging.info(f"Event added: {title} on {date_display}{time_display}")
        return f"Event '{title}' added for {date_display}{time_display}."
    except Exception as e:
        logging.error(f"Error adding event: {e}")
        return f"Failed to add event: {str(e)}"


def _parse_event_date(date_str: str) -> datetime:
    """Parse date strings like '2024-03-15', 'tomorrow', 'monday', 'next friday'."""
    date_str = date_str.strip().lower()
    now = datetime.now()

    if date_str == "today":
        return now
    if date_str == "tomorrow":
        return now + timedelta(days=1)

    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    # Handle "next monday" or just "monday"
    clean = date_str.replace("next ", "")
    if clean in days:
        target = days.index(clean)
        current = now.weekday()
        diff = (target - current) % 7
        if diff == 0:
            diff = 7
        return now + timedelta(days=diff)

    # Try ISO format
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        pass

    # Try common formats
    for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%B %d", "%b %d"]:
        try:
            parsed = datetime.strptime(date_str, fmt)
            if parsed.year == 1900:
                parsed = parsed.replace(year=now.year)
            return parsed
        except ValueError:
            continue

    raise ValueError(f"Could not parse date: {date_str}")


@function_tool()
async def list_events(
    context: RunContext,  # type: ignore
    period: Optional[str] = "week",
) -> str:
    """
    List upcoming events from the calendar.

    Args:
        period: Time period to show - today, week, or month. Defaults to week.
    """
    try:
        events = _load_json(EVENTS_FILE)
        now = datetime.now()

        if period == "today":
            end = now.replace(hour=23, minute=59, second=59)
        elif period == "month":
            end = now + timedelta(days=30)
        else:
            end = now + timedelta(days=7)

        upcoming = []
        for e in events:
            event_date = datetime.fromisoformat(e["date"])
            if now.date() <= event_date.date() <= end.date():
                upcoming.append(e)

        upcoming.sort(key=lambda e: e["date"])

        if not upcoming:
            return f"No events this {period}."

        lines = []
        for e in upcoming:
            d = datetime.fromisoformat(e["date"]).strftime("%A, %b %d")
            time_str = f" at {e['time']}" if e.get("time") else ""
            lines.append(f"- {e['title']} on {d}{time_str}")
        return f"Upcoming events ({period}):\n" + "\n".join(lines)
    except Exception as e:
        logging.error(f"Error listing events: {e}")
        return f"Failed to list events: {str(e)}"


@function_tool()
async def delete_event(
    context: RunContext,  # type: ignore
    event_id: str,
) -> str:
    """
    Delete an event from the calendar.

    Args:
        event_id: The ID of the event to delete.
    """
    try:
        events = _load_json(EVENTS_FILE)
        original_len = len(events)
        events = [e for e in events if e["id"] != event_id]
        if len(events) == original_len:
            return f"No event found with id: {event_id}"
        _save_json(EVENTS_FILE, events)
        return "Event deleted."
    except Exception as e:
        logging.error(f"Error deleting event: {e}")
        return f"Failed to delete event: {str(e)}"


# ============================================================
# SMS (Termii)
# ============================================================

TERMII_BASE_URL = "https://v3.api.termii.com/api"


@function_tool()
async def send_sms(
    context: RunContext,  # type: ignore
    to_number: str,
    message: str,
) -> str:
    """
    Send an SMS text message to a phone number using Termii.

    Args:
        to_number: The recipient phone number e.g. 2348012345678 (no + prefix).
        message: The text message to send.
    """
    try:
        api_key = os.getenv("TERMII_API_KEY")
        sender_id = os.getenv("TERMII_SENDER_ID", "Dan")
        if not api_key:
            return "SMS failed: TERMII_API_KEY not configured in .env file."

        # Remove + prefix if present
        to_number = to_number.lstrip("+")

        payload = {
            "to": to_number,
            "from": sender_id,
            "sms": message,
            "type": "plain",
            "channel": "generic",
            "api_key": api_key,
        }

        response = requests.post(f"{TERMII_BASE_URL}/sms/send", json=payload)
        data = response.json()

        if response.status_code == 200 and data.get("message_id"):
            logging.info(f"SMS sent to {to_number}: {data.get('message_id')}")
            return f"SMS sent successfully to {to_number}."
        else:
            error_msg = data.get("message", "Unknown error")
            logging.error(f"Termii SMS failed: {error_msg}")
            return f"SMS failed: {error_msg}"
    except Exception as e:
        logging.error(f"Error sending SMS: {e}")
        return f"Failed to send SMS: {str(e)}"


@function_tool()
async def check_sms_balance(
    context: RunContext,  # type: ignore
) -> str:
    """
    Check the remaining SMS balance on Termii.
    """
    try:
        api_key = os.getenv("TERMII_API_KEY")
        if not api_key:
            return "Balance check failed: TERMII_API_KEY not configured."

        response = requests.get(f"{TERMII_BASE_URL}/get-balance", params={"api_key": api_key})
        data = response.json()

        if response.status_code == 200:
            balance = data.get("balance", "unknown")
            currency = data.get("currency", "NGN")
            return f"Termii balance: {balance} {currency}."
        else:
            return "Could not retrieve balance."
    except Exception as e:
        logging.error(f"Error checking SMS balance: {e}")
        return f"Failed to check balance: {str(e)}"


# ============================================================
# PHONE CALLS (LiveKit SIP)
# ============================================================

@function_tool()
async def make_phone_call(
    context: RunContext,  # type: ignore
    phone_number: str,
) -> str:
    """
    Make an outbound phone call to a number. The agent will be able to talk
    to the person on the other end through the LiveKit SIP trunk.

    Args:
        phone_number: The phone number to call in international format like +2348012345678.
    """
    try:
        trunk_id = os.getenv("LIVEKIT_SIP_OUTBOUND_TRUNK")
        if not trunk_id:
            return "Phone call failed: LIVEKIT_SIP_OUTBOUND_TRUNK not configured in .env file."

        session = context.session
        job_ctx = session._job_ctx

        sip_participant = await job_ctx.add_sip_participant(
            call_to=phone_number,
            trunk_id=trunk_id,
            participant_identity=f"call_{phone_number}",
            participant_name=f"Call to {phone_number}",
        )
        logging.info(f"Phone call initiated to {phone_number}")
        return f"Calling {phone_number} now. The person will join this conversation when they pick up."
    except Exception as e:
        logging.error(f"Error making phone call: {e}")
        return f"Failed to make phone call: {str(e)}"