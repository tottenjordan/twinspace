"""Tests for video monitoring tools."""
from unittest.mock import MagicMock

import pytest

from app.appliance_agent.tools.video_monitor import (
    VideoFrameBuffer,
    monitor_video_stream,
    request_frame_analysis,
)


@pytest.fixture
def video_buffer():
    """Create a fresh VideoFrameBuffer instance."""
    buffer = VideoFrameBuffer()
    buffer.clear()
    return buffer


def test_video_frame_buffer_singleton():
    """Test that VideoFrameBuffer is a singleton."""
    buffer1 = VideoFrameBuffer()
    buffer2 = VideoFrameBuffer()
    assert buffer1 is buffer2


def test_video_frame_buffer_add_frame(video_buffer):
    """Test adding frames to the buffer."""
    frame_data = b"fake_image_data"
    video_buffer.add_frame(frame_data, "image/jpeg")

    assert video_buffer.get_frame_count() == 1
    latest = video_buffer.get_latest_frame()
    assert latest["data"] == frame_data
    assert latest["mime_type"] == "image/jpeg"
    assert "timestamp" in latest


def test_video_frame_buffer_max_capacity(video_buffer):
    """Test that buffer keeps only last 10 frames."""
    for i in range(15):
        video_buffer.add_frame(f"frame_{i}".encode(), "image/jpeg")

    assert video_buffer.get_frame_count() == 10
    latest = video_buffer.get_latest_frame()
    assert latest["data"] == b"frame_14"


def test_video_frame_buffer_get_latest_frame_empty(video_buffer):
    """Test getting latest frame from empty buffer."""
    assert video_buffer.get_latest_frame() is None
    assert video_buffer.get_latest_timestamp() is None


def test_video_frame_buffer_clear(video_buffer):
    """Test clearing the buffer."""
    video_buffer.add_frame(b"frame_data", "image/jpeg")
    assert video_buffer.get_frame_count() == 1

    video_buffer.clear()
    assert video_buffer.get_frame_count() == 0
    assert video_buffer.get_latest_frame() is None


async def test_monitor_video_stream_no_frames():
    """Test monitor_video_stream with no frames."""
    buffer = VideoFrameBuffer()
    buffer.clear()

    tool_context = MagicMock()
    tool_context.state = {}

    result = await monitor_video_stream(tool_context)

    assert result["status"] == "no_frames"
    assert result["frame_count"] == 0
    assert "no video frames" in result["message"].lower()


async def test_monitor_video_stream_with_frames():
    """Test monitor_video_stream with active video stream."""
    buffer = VideoFrameBuffer()
    buffer.clear()
    buffer.add_frame(b"test_frame_data", "image/jpeg")

    tool_context = MagicMock()
    tool_context.state = {}

    result = await monitor_video_stream(tool_context)

    assert result["status"] == "receiving"
    assert result["frame_count"] == 1
    assert "latest_frame_timestamp" in result
    assert result["frame_size_bytes"] == len(b"test_frame_data")
    assert tool_context.state["video_frames_received"] == 1
    assert "last_video_frame_timestamp" in tool_context.state


def test_request_frame_analysis_no_frames():
    """Test request_frame_analysis with no frames."""
    buffer = VideoFrameBuffer()
    buffer.clear()

    tool_context = MagicMock()
    tool_context.state = {}

    result = request_frame_analysis(tool_context)

    assert result["status"] == "no_frames"
    assert "wait" in result["instruction"].lower()


def test_request_frame_analysis_with_frames():
    """Test request_frame_analysis with available frames."""
    buffer = VideoFrameBuffer()
    buffer.clear()
    buffer.add_frame(b"test_frame", "image/jpeg")

    tool_context = MagicMock()
    tool_context.state = {}

    result = request_frame_analysis(tool_context)

    assert result["status"] == "ready"
    assert "examine" in result["instruction"].lower()
    assert "detect_appliance" in result["instruction"]
    assert "latest_frame_timestamp" in result


def test_multiple_frames_keep_latest(video_buffer):
    """Test that multiple frames are stored and latest is accessible."""
    video_buffer.add_frame(b"frame_1", "image/jpeg")
    video_buffer.add_frame(b"frame_2", "image/jpeg")
    video_buffer.add_frame(b"frame_3", "image/jpeg")

    assert video_buffer.get_frame_count() == 3

    latest = video_buffer.get_latest_frame()
    assert latest["data"] == b"frame_3"


async def test_monitor_video_stream_multiple_calls():
    """Test that monitor_video_stream can be called multiple times."""
    buffer = VideoFrameBuffer()
    buffer.clear()

    tool_context = MagicMock()
    tool_context.state = {}

    # First call with no frames
    result = await monitor_video_stream(tool_context)
    assert result["status"] == "no_frames"

    # Add a frame
    buffer.add_frame(b"frame_1", "image/jpeg")

    # Second call should see the frame
    result = await monitor_video_stream(tool_context)
    assert result["status"] == "receiving"
    assert result["frame_count"] == 1

    # Add another frame
    buffer.add_frame(b"frame_2", "image/jpeg")

    # Third call should see both frames
    result = await monitor_video_stream(tool_context)
    assert result["status"] == "receiving"
    assert result["frame_count"] == 2
