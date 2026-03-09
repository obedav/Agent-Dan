import asyncio
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    noise_cancellation,
)
from livekit.plugins import google
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from livekit.agents.beta.tools import EndCallTool
from tools import (
    get_weather, search_web, send_email,
    remember, recall,
    add_task, list_tasks, complete_task, delete_task,
    set_reminder, list_reminders, check_due_reminders,
    add_event, list_events, delete_event,
    send_sms, check_sms_balance, make_phone_call,
)

load_dotenv()


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                voice="Aoede",
                temperature=0.8,
            ),
            tools=[
                get_weather,
                search_web,
                send_email,
                remember,
                recall,
                add_task,
                list_tasks,
                complete_task,
                delete_task,
                set_reminder,
                list_reminders,
                add_event,
                list_events,
                delete_event,
                send_sms,
                check_sms_balance,
                make_phone_call,
                EndCallTool(),
            ],
        )


async def _reminder_loop(session: AgentSession):
    """Background loop that checks for due reminders every 30 seconds."""
    while True:
        await asyncio.sleep(30)
        due = check_due_reminders()
        for r in due:
            await session.generate_reply(
                instructions=f"A reminder is due! Notify the user: '{r['reminder']}'. "
                "Be proactive and say it clearly."
            )


async def entrypoint(ctx: agents.JobContext):
    session = AgentSession()

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()

    # Start background reminder checker
    asyncio.create_task(_reminder_loop(session))

    await session.generate_reply(
        instructions=SESSION_INSTRUCTION,
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
