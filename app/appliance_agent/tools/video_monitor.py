"""Video stream monitoring tool for appliance detection."""
from collections import deque
from datetime import datetime

from google.adk.tools.tool_context import ToolContext


class VideoFrameBuffer:
    """Singleton buffer for storing recent video frames."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize buffer if not already initialized."""
        if not VideoFrameBuffer._initialized:
            self._frames: deque[dict] = deque(maxlen=10)  # Keep last 10 frames
            self._latest_timestamp = None
            self._total_frames = 0  # Total frames received (continuously increments)
            VideoFrameBuffer._initialized = True

    def add_frame(self, frame_data: bytes, mime_type: str = "image/jpeg") -> None:
        """Add a frame to the buffer.

        Args:
            frame_data: Binary image data
            mime_type: MIME type of the image
        """
        self._total_frames += 1
        self._frames.append({
            "data": frame_data,
            "mime_type": mime_type,
            "timestamp": datetime.now().isoformat(),
        })
        self._latest_timestamp = datetime.now().isoformat()

    def get_latest_frame(self) -> dict | None:
        """Get the most recent frame.

        Returns:
            Dictionary with frame data and metadata, or None if no frames
        """
        if not self._frames:
            return None
        return self._frames[-1]

    def get_frame_count(self) -> int:
        """Get the number of frames in the buffer.

        Returns:
            Number of buffered frames (max 10)
        """
        return len(self._frames)

    def get_total_frames(self) -> int:
        """Get the total number of frames received.

        Returns:
            Total frames received since session started
        """
        return self._total_frames

    def get_latest_timestamp(self) -> str | None:
        """Get timestamp of the latest frame.

        Returns:
            ISO format timestamp or None
        """
        return self._latest_timestamp

    def clear(self) -> None:
        """Clear all frames from the buffer."""
        self._frames.clear()
        self._latest_timestamp = None


async def monitor_video_stream(tool_context: ToolContext) -> dict:
    """Monitor the video stream and check for new frames.

    This tool checks the current status of the video stream and returns
    information about frame receipt and stream health.

    Args:
        tool_context: Tool context for accessing session state

    Returns:
        Dictionary with video stream status and frame information
    """
    buffer = VideoFrameBuffer()
    frame_count = buffer.get_frame_count()
    latest_timestamp = buffer.get_latest_timestamp()

    if frame_count == 0:
        return {
            "status": "no_frames",
            "message": "No video frames received yet. Waiting for video stream...",
            "frame_count": 0,
        }

    latest_frame = buffer.get_latest_frame()

    # Update session state with latest frame info
    tool_context.state["last_video_frame_timestamp"] = latest_timestamp
    tool_context.state["video_frames_received"] = frame_count

    return {
        "status": "receiving",
        "message": "Video stream active. Receiving frames at ~1 FPS.",
        "frame_count": frame_count,
        "latest_frame_timestamp": latest_timestamp,
        "frame_size_bytes": len(latest_frame["data"]),
        "note": "The video frames are visible to you through the Live API. "
                "Analyze what you see to detect appliances.",
    }


def request_frame_analysis(tool_context: ToolContext) -> dict:
    """Request explicit analysis of the current video frame.

    Use this tool when you want to actively analyze what's currently visible
    in the video stream to detect appliances. The video frames are already
    being sent to you through the Live API, so you can see them directly.

    This tool serves as a reminder to carefully examine the current video
    frame and report any appliances you detect.

    Args:
        tool_context: Tool context for accessing session state

    Returns:
        Dictionary prompting analysis of current frame
    """
    buffer = VideoFrameBuffer()

    if buffer.get_frame_count() == 0:
        return {
            "status": "no_frames",
            "instruction": "No video frames available. Wait for user to start camera.",
        }

    latest_frame = buffer.get_latest_frame()

    return {
        "status": "ready",
        "instruction": (
            "Examine the current video frame carefully. Look for home appliances "
            "(refrigerator, oven, dishwasher, microwave, washing machine, dryer, etc.). "
            "If you detect an appliance:\n"
            "1. Call detect_appliance with the appliance type\n"
            "2. Ask the user if they want to add it to inventory\n"
            "3. Use confirm_appliance_detection with their response"
        ),
        "latest_frame_timestamp": latest_frame["timestamp"],
        "note": "You can see the video frames directly through the Live API.",
    }
