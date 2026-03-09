# 🧠 Dan - Your Personal AI Assistant

A real-time voice-powered AI assistant built with Python and LiveKit, inspired by the AI from Iron Man. Dan speaks like a classy butler, manages your life, and keeps things running smoothly.

## Features

- 🗣️ **Voice Conversations** — Real-time speech using Google Gemini Realtime
- 🔍 **Web Search** — Search the internet via DuckDuckGo
- 🌤️ **Weather** — Get current weather for any city
- 📨 **Email** — Send emails through Gmail
- 📝 **Task Management** — Add, list, complete, and delete to-do items
- ⏰ **Reminders** — Set timed reminders with automatic notifications
- 📅 **Calendar** — Manage events with natural date parsing
- 💬 **SMS** — Send and receive text messages via Termii
- 📞 **Phone Calls** — Make outbound calls and talk through the agent
- 🧠 **Memory** — Remembers your preferences and personal info across sessions
- 🔇 **Noise Cancellation** — Built-in background noise filtering

## Prerequisites

- Python 3.10+
- A [LiveKit Cloud](https://cloud.livekit.io) account (free tier available)
- API keys for the services you want to use

## Setup

1. Clone the repo
   ```bash
   git clone https://github.com/obedav/Agent-Dan.git
   cd Agent-Dan
   ```

2. Create and activate a virtual environment
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API keys
   ```env
   LIVEKIT_URL=your_livekit_url
   LIVEKIT_API_KEY=your_api_key
   LIVEKIT_API_SECRET=your_api_secret
   GOOGLE_API_KEY=your_google_api_key

   # Optional - for email
   GMAIL_USER=your_email@gmail.com
   GMAIL_APP_PASSWORD=your_app_password

   # Optional - for SMS
   TERMII_API_KEY=your_termii_key

   # Optional - for phone calls
   LIVEKIT_SIP_TRUNK_ID=your_sip_trunk_id
   ```

5. Make sure your LiveKit Cloud account is set up correctly

## Usage

```bash
python agent.py dev
```

Then open the [LiveKit Playground](https://cloud.livekit.io/playground) to connect and start talking to Dan.

## Tech Stack

- **LiveKit Agents** — Real-time voice agent framework
- **Google Gemini** — Realtime LLM for conversation
- **DuckDuckGo** — Web search
- **Termii** — SMS messaging
- **LiveKit SIP** — Phone call support
