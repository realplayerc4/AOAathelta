"""
WebSocket topic subscriber with auto-reconnect.
"""
import json
import threading
import time
from typing import Callable, Iterable, Optional

import websocket


class TopicSubscriber:
    """Subscribe to topics from the AMR WebSocket endpoint."""

    def __init__(
        self,
        url: str,
        topics: Iterable[str] | None = None,
        on_message: Callable[[str, dict], None] | None = None,
        on_error: Optional[Callable[[str], None]] = None,
        reconnect_delay: float = 3.0,
    ) -> None:
        self.url = url
        self.topics = set(topics) if topics else set()
        self.on_message = on_message or (lambda t, p: None)
        self.on_error = on_error
        self.reconnect_delay = reconnect_delay
        self._stop = False
        self._thread: Optional[threading.Thread] = None
        self._ws: Optional[websocket.WebSocketApp] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop = True
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=1.0)

    def enable_topic(self, topic: str) -> None:
        """Enable subscription to a topic."""
        self.topics.add(topic)
        if self._ws and self._ws.sock:
            try:
                self._ws.send(json.dumps({"enable_topic": topic}))
            except Exception:
                pass

    def disable_topic(self, topic: str) -> None:
        """Disable subscription to a topic."""
        self.topics.discard(topic)
        if self._ws and self._ws.sock:
            try:
                self._ws.send(json.dumps({"disable_topic": topic}))
            except Exception:
                pass

    def _send_topic_subscriptions(self) -> None:
        """Send subscription commands for all tracked topics."""
        if not self._ws or not self._ws.sock:
            return
        for topic in self.topics:
            try:
                self._ws.send(json.dumps({"enable_topic": topic}))
            except Exception:
                pass

    def _run(self) -> None:
        while not self._stop:
            try:
                self._ws = websocket.WebSocketApp(
                    self.url,
                    on_message=self._on_raw_message,
                    on_error=self._on_raw_error,
                    on_close=self._on_raw_close,
                    on_open=self._on_raw_open,
                )
                self._ws.run_forever()
            except Exception as exc:
                if self.on_error:
                    self.on_error(f"connect error: {exc}")
            if not self._stop:
                time.sleep(self.reconnect_delay)

    def _on_raw_open(self, ws):
        """连接建立后发送订阅指令"""
        self._send_topic_subscriptions()

    # --- callbacks for WebSocketApp ---
    def _on_raw_message(self, ws, message: str):
        try:
            data = json.loads(message)
        except Exception:
            data = message
        topic = None
        payload = data
        if isinstance(data, dict):
            topic = data.get("topic")
        if topic and topic in self.topics:
            try:
                self.on_message(topic, payload)
            except Exception:
                # Avoid crashing the thread on callback errors
                if self.on_error:
                    self.on_error("callback error")

    def _on_raw_error(self, ws, error):
        if self.on_error:
            self.on_error(str(error))

    def _on_raw_close(self, ws, code, reason):
        if self.on_error:
            self.on_error(f"closed: {code} {reason}")
