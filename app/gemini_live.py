"""Gemini Live API wrapper for bidirectional streaming."""
import asyncio
import inspect
from typing import Any, AsyncIterator, Callable

from google import genai
from google.genai import types


class GeminiLive:
    """Wrapper for Gemini Live API with multimodal streaming support."""

    def __init__(
        self,
        *,
        model: str = "gemini-2.5-flash-native-audio-preview-12-2025",
        system_instruction: str | None = None,
        tools: list[Callable] | None = None,
        input_sample_rate: int = 16000,
        output_sample_rate: int = 24000,
        voice_name: str = "Puck",
    ):
        """Initialize Gemini Live client.

        Args:
            model: Model name to use
            system_instruction: System instruction for the agent
            tools: List of Python functions to register as tools
            input_sample_rate: Audio input sample rate (Hz)
            output_sample_rate: Audio output sample rate (Hz)
            voice_name: Voice name for audio output
        """
        self.client = genai.Client()
        self.model = model
        self.system_instruction = system_instruction
        self.tools = tools or []
        self.input_sample_rate = input_sample_rate
        self.output_sample_rate = output_sample_rate
        self.voice_name = voice_name

        # Tool name to function mapping
        self.tool_map = {tool.__name__: tool for tool in self.tools}

    async def start_session(
        self,
        *,
        audio_input_queue: asyncio.Queue,
        video_input_queue: asyncio.Queue,
        text_input_queue: asyncio.Queue,
        audio_output_callback: Callable[[bytes], Any] | None = None,
        on_interrupt: Callable[[], Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Start a Live API session with bidirectional streaming.

        Args:
            audio_input_queue: Queue for audio input chunks (bytes)
            video_input_queue: Queue for video frames (bytes)
            text_input_queue: Queue for text messages (str)
            audio_output_callback: Callback for audio output chunks
            on_interrupt: Callback when agent is interrupted

        Yields:
            Event dictionaries from the Live API
        """
        # Build config
        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice_name
                    )
                )
            ),
        )

        if self.system_instruction:
            config.system_instruction = types.Content(
                parts=[types.Part(text=self.system_instruction)]
            )

        if self.tools:
            config.tools = self.tools

        # Connect to Live API
        print(f"Connecting to Live API with model: {self.model}")
        async with self.client.aio.live.connect(
            model=self.model, config=config
        ) as session:
            print("Live API session connected successfully")
            # Send audio chunks from queue
            async def send_audio():
                chunk_count = 0
                while True:
                    chunk = await audio_input_queue.get()
                    if chunk is None:  # Sentinel to stop
                        break
                    chunk_count += 1
                    print(f">>> Sending audio chunk #{chunk_count} to Live API: {len(chunk)} bytes")
                    await session.send_realtime_input(
                        audio=types.Blob(
                            data=chunk,
                            mime_type=f"audio/pcm;rate={self.input_sample_rate}",
                        )
                    )
                    print(f">>> Audio chunk #{chunk_count} sent successfully")

            # Send video frames from queue
            async def send_video():
                while True:
                    frame = await video_input_queue.get()
                    if frame is None:  # Sentinel to stop
                        break
                    await session.send_realtime_input(
                        video=types.Blob(
                            data=frame,
                            mime_type="image/jpeg",
                        )
                    )

            # Send text messages from queue
            async def send_text():
                while True:
                    message = await text_input_queue.get()
                    if message is None:  # Sentinel to stop
                        break
                    # Skip empty messages but still signal turn completion
                    if message == "":
                        # Send turn complete signal without text
                        print(">>> Sending turn_complete signal to Live API")
                        # Use a space instead of empty string to avoid validation error
                        await session.send(input=" ", end_of_turn=True)
                    else:
                        await session.send(input=message, end_of_turn=True)

            # Event queue for passing events from receive_loop to caller
            event_queue = asyncio.Queue()

            # Receive events from Live API
            async def receive_loop():
                try:
                    print("Starting receive_loop - listening for events...")
                    async for response in session.receive():
                        print(f"Raw response received, checking attributes...")
                        # Handle server content
                        server_content = response.server_content
                        if server_content:
                            print(f"  server_content: model_turn={bool(server_content.model_turn)}, "
                                  f"turn_complete={bool(server_content.turn_complete)}, "
                                  f"interrupted={bool(server_content.interrupted)}")
                            # Handle model turn (audio/text responses)
                            if server_content.model_turn:
                                for part in server_content.model_turn.parts:
                                    # Audio output
                                    if part.inline_data:
                                        audio_data = part.inline_data.data
                                        if audio_output_callback:
                                            if inspect.iscoroutinefunction(audio_output_callback):
                                                await audio_output_callback(audio_data)
                                            else:
                                                audio_output_callback(audio_data)

                                    # Text output
                                    if part.text:
                                        await event_queue.put({
                                            "type": "text_output",
                                            "text": part.text,
                                        })

                            # Handle turn complete
                            if server_content.turn_complete:
                                await event_queue.put({"type": "turn_complete"})

                            # Handle interruption
                            if server_content.interrupted:
                                if on_interrupt:
                                    if inspect.iscoroutinefunction(on_interrupt):
                                        await on_interrupt()
                                    else:
                                        on_interrupt()
                                await event_queue.put({"type": "interrupted"})

                        # Handle tool calls (on response, not server_content)
                        if response.tool_call:
                            tool_call = response.tool_call
                            tool_responses = []

                            for fc in tool_call.function_calls:
                                function_name = fc.name
                                args = fc.args

                                # Execute the tool
                                if function_name in self.tool_map:
                                    try:
                                        result = self.tool_map[function_name](**args)
                                        if inspect.isawaitable(result):
                                            result = await result
                                        tool_responses.append(
                                            types.FunctionResponse(
                                                id=fc.id,
                                                name=function_name,
                                                response=result,
                                            )
                                        )
                                        await event_queue.put({
                                            "type": "tool_call",
                                            "function_name": function_name,
                                            "args": args,
                                            "result": result,
                                        })
                                    except Exception as e:
                                        error_response = {"error": str(e)}
                                        tool_responses.append(
                                            types.FunctionResponse(
                                                id=fc.id,
                                                name=function_name,
                                                response=error_response,
                                            )
                                        )
                                        await event_queue.put({
                                            "type": "tool_error",
                                            "function_name": function_name,
                                            "error": str(e),
                                        })

                            # Send tool responses back
                            if tool_responses:
                                await session.send_tool_response(
                                    function_responses=tool_responses
                                )

                        # Handle tool call cancel
                        if response.tool_call_cancellation:
                            await event_queue.put({"type": "tool_call_cancelled"})

                        # Handle setup complete
                        if response.setup_complete:
                            await event_queue.put({"type": "setup_complete"})

                except Exception as e:
                    await event_queue.put({"type": "error", "error": str(e)})
                finally:
                    # Signal completion
                    await event_queue.put(None)

            # Start all tasks in background
            audio_task = asyncio.create_task(send_audio())
            video_task = asyncio.create_task(send_video())
            text_task = asyncio.create_task(send_text())
            receive_task = asyncio.create_task(receive_loop())

            try:
                # Yield events from queue
                while True:
                    event = await event_queue.get()
                    if event is None:
                        break
                    yield event
            finally:
                # Cancel all tasks when done
                audio_task.cancel()
                video_task.cancel()
                text_task.cancel()
                receive_task.cancel()

                # Wait for cancellation to complete
                await asyncio.gather(
                    audio_task, video_task, text_task, receive_task,
                    return_exceptions=True
                )
