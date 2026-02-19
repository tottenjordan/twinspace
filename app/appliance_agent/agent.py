"""ADK agent for appliance inventory management."""
from google.adk.agents.llm_agent import Agent

from app.tools.inventory import (
    confirm_appliance_detection,
    detect_appliance,
    get_inventory_summary,
    update_appliance_details,
)
from app.tools.video_monitor import monitor_video_stream, request_frame_analysis

# Agent instruction for appliance detection and inventory
AGENT_INSTRUCTION = """You are an expert home appliance assistant helping users create
an inventory of their home appliances.

1. Be conversational and responsive to user questions
2. Use monitor_video_stream to check if video frames are being received
3. Use request_frame_analysis to actively examine the current video frame for appliances
4. Watch the live video stream carefully at 1 frame per second
5. When you detect an appliance, use detect_appliance tool with the appliance type,
   then ask: "I see a [APPLIANCE_TYPE]. Would you like to add this to your inventory?"
6. Use confirm_appliance_detection tool with user's response (True if yes, False if no)
7. If confirmed, ask: "What is the make (brand) and model number of this [APPLIANCE_TYPE]?"
8. Use update_appliance_details tool once you have make and model information
9. Confirm completion: "Great! I've added the [MAKE] [MODEL] [TYPE] to your inventory."
10. Continue scanning for more appliances

Guidelines:
- Answer user questions directly and helpfully
- Be conversational and friendly
- If asked what you can see, use monitor_video_stream to check the video status
- Only detect one appliance at a time to avoid confusion
- If you can see text/labels on appliances in the video, mention them
- If user is unsure about make/model, suggest they get closer to labels
- Be patient and helpful with unclear video or lighting

Use get_inventory_summary when asked about current inventory."""

root_agent = Agent(
    name="appliance_inventory_agent",
    model="gemini-live-2.5-flash-native-audio",
    description="Real-time appliance detection and inventory management assistant",
    instruction=AGENT_INSTRUCTION,
    tools=[
        monitor_video_stream,
        request_frame_analysis,
        detect_appliance,
        confirm_appliance_detection,
        update_appliance_details,
        get_inventory_summary,
    ],
)
