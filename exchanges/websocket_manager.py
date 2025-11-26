"""Base WebSocket Manager implementation for all exchanges"""

import time
import json
import threading
from typing import Optional, Callable, Dict, Any, List
from abc import abstractmethod
import websocket
import logging
from queue import Queue, Empty
from dataclasses import dataclass

from .base import WebSocketState, WebSocketMessage, WebSocketProtocol


logger = logging.getLogger(__name__)


@dataclass
class ReconnectConfig:
    """Configuration for WebSocket reconnection"""
    enabled: bool = True
    initial_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    multiplier: float = 1.5
    max_attempts: int = -1  # -1 for infinite


class BaseWebSocketManager(WebSocketProtocol):
    """
    Base WebSocket manager with common functionality for all exchanges.

    Features:
    - Automatic reconnection with exponential backoff
    - Thread-safe message handling
    - Heartbeat/ping-pong support
    - Subscription management
    - Error handling and logging
    """

    def __init__(self,
                 exchange_name: str,
                 on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
                 on_error: Optional[Callable[[Exception], None]] = None,
                 on_state_change: Optional[Callable[[WebSocketState], None]] = None,
                 reconnect_config: Optional[ReconnectConfig] = None):
        """
        Initialize WebSocket manager.

        Args:
            exchange_name: Name of the exchange for logging
            on_message: Callback for processed messages
            on_error: Callback for errors
            on_state_change: Callback for connection state changes
            reconnect_config: Configuration for automatic reconnection
        """
        self.exchange_name = exchange_name
        self.on_message = on_message
        self.on_error = on_error
        self.on_state_change = on_state_change

        # Connection state
        self._state = WebSocketState.DISCONNECTED
        self._ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._url: Optional[str] = None

        # Reconnection
        self.reconnect_config = reconnect_config or ReconnectConfig()
        self._reconnect_attempts = 0
        self._reconnect_delay = self.reconnect_config.initial_delay
        self._should_reconnect = False

        # Message handling
        self._message_queue = Queue()
        self._message_thread: Optional[threading.Thread] = None
        self._running = False

        # Subscription tracking
        self._subscriptions: List[Dict[str, Any]] = []
        self._pending_subscriptions: List[Dict[str, Any]] = []

        # Heartbeat
        self._last_ping_time = 0
        self._last_pong_time = 0
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_interval = 30  # seconds

        # Threading
        self._lock = threading.Lock()

    def connect(
            self,
            url: str,
            on_open: Callable = None,
            on_close: Callable = None) -> bool:
        """
        Connect to WebSocket endpoint.

        Args:
            url: WebSocket URL
            on_open: Optional callback when connection opens
            on_close: Optional callback when connection closes

        Returns:
            True if connection initiated successfully
        """
        with self._lock:
            if self._state not in [
                    WebSocketState.DISCONNECTED,
                    WebSocketState.ERROR]:
                logger.warning(
                    f"{self.exchange_name}: Already connected or connecting")
                return False

            self._url = url
            self._should_reconnect = True
            self._set_state(WebSocketState.CONNECTING)

            # Create WebSocket application
            self._ws = websocket.WebSocketApp(
                url,
                on_open=lambda ws: self._on_open(
                    ws,
                    on_open),
                on_close=lambda ws,
                code,
                msg: self._on_close(
                    ws,
                    code,
                    msg,
                    on_close),
                on_message=self._on_message_raw,
                on_error=self._on_error,
                on_ping=self._on_ping,
                on_pong=self._on_pong)

            # Start WebSocket thread
            self._running = True
            self._ws_thread = threading.Thread(
                target=self._run_websocket,
                name=f"{self.exchange_name}-WebSocket",
                daemon=True
            )
            self._ws_thread.start()

            # Start message processing thread
            self._message_thread = threading.Thread(
                target=self._process_messages,
                name=f"{self.exchange_name}-MessageProcessor",
                daemon=True
            )
            self._message_thread.start()

            # Start heartbeat thread
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                name=f"{self.exchange_name}-Heartbeat",
                daemon=True
            )
            self._heartbeat_thread.start()

            return True

    def disconnect(self):
        """Disconnect from WebSocket"""
        with self._lock:
            logger.info(f"{self.exchange_name}: Disconnecting WebSocket")
            self._should_reconnect = False
            self._running = False

            if self._ws:
                self._ws.close()

            self._set_state(WebSocketState.DISCONNECTED)

        # Wait for threads to finish (outside of lock to prevent deadlock)
        threads_to_join = []
        if hasattr(
                self,
                '_ws_thread') and self._ws_thread and self._ws_thread.is_alive():
            threads_to_join.append(self._ws_thread)
        if hasattr(
                self,
                '_message_thread') and self._message_thread and self._message_thread.is_alive():
            threads_to_join.append(self._message_thread)
        has_heartbeat = (hasattr(self, '_heartbeat_thread') and
                         self._heartbeat_thread and self._heartbeat_thread.is_alive())
        if has_heartbeat:
            threads_to_join.append(self._heartbeat_thread)

        # Give threads a moment to finish gracefully
        for thread in threads_to_join:
            thread.join(timeout=2.0)
            if thread.is_alive():
                logger.warning(
                    f"{self.exchange_name}: Thread {thread.name} did not terminate gracefully")

    def send(self, message: Dict[str, Any]) -> bool:
        """
        Send message to WebSocket.

        Args:
            message: Message to send

        Returns:
            True if sent successfully
        """
        if not self.is_connected():
            logger.warning(
                f"{self.exchange_name}: Cannot send message - not connected")
            return False

        try:
            message_str = json.dumps(message)
            self._ws.send(message_str)
            logger.debug(f"{self.exchange_name}: Sent message: {message_str}")
            return True
        except Exception as e:
            logger.error(f"{self.exchange_name}: Error sending message: {e}")
            self._handle_error(e)
            return False

    def subscribe(self, channels: List[Dict[str, Any]]) -> bool:
        """
        Subscribe to channels.

        Args:
            channels: List of channel configurations

        Returns:
            True if subscription request sent successfully
        """
        if not channels:
            return True

        # Add to subscription tracking (with limit check)
        with self._lock:
            # Check if we're approaching the subscription limit
            max_subscriptions = 250  # Safe limit for BitUnix
            current_count = len(self._subscriptions)

            if current_count + len(channels) > max_subscriptions:
                logger.warning(
                    f"{self.exchange_name}: Subscription limit reached "
                    f"({current_count} + {len(channels)} > {max_subscriptions})")
                # Only add what we can
                available_slots = max(0, max_subscriptions - current_count)
                if available_slots > 0:
                    channels = channels[:available_slots]
                    logger.info(
                        f"{self.exchange_name}: Limited to {available_slots} new subscriptions")
                else:
                    logger.error(
                        f"{self.exchange_name}: Cannot add more subscriptions, limit reached")
                    return False

            self._subscriptions.extend(channels)

            if not self.is_connected():
                # Queue for when connected (avoid duplicates)
                new_channels = []
                for channel in channels:
                    # Convert to string for comparison to avoid dict comparison
                    # issues
                    channel_str = json.dumps(channel, sort_keys=True)
                    existing_strs = [
                        json.dumps(
                            c, sort_keys=True) for c in self._pending_subscriptions]
                    if channel_str not in existing_strs:
                        self._pending_subscriptions.append(channel)
                        new_channels.append(channel)
                if new_channels:
                    logger.info(
                        f"{self.exchange_name}: Queued {len(new_channels)} new subscriptions")
                return True

        # Send subscription request
        return self._send_subscription_request(channels, True)

    def unsubscribe(self, channels: List[Dict[str, Any]]) -> bool:
        """
        Unsubscribe from channels.

        Args:
            channels: List of channel configurations

        Returns:
            True if unsubscription request sent successfully
        """
        if not channels or not self.is_connected():
            return False

        # Remove from subscription tracking
        with self._lock:
            for channel in channels:
                if channel in self._subscriptions:
                    self._subscriptions.remove(channel)

        # Send unsubscription request
        return self._send_subscription_request(channels, False)

    def is_connected(self) -> bool:
        """Check if connected"""
        return self._state in [
            WebSocketState.CONNECTED,
            WebSocketState.AUTHENTICATED]

    def get_state(self) -> str:
        """Get connection state"""
        return self._state

    @abstractmethod
    def _send_subscription_request(
            self, channels: List[Dict[str, Any]], subscribe: bool) -> bool:
        """
        Send subscription/unsubscription request.
        Must be implemented by exchange-specific subclass.

        Args:
            channels: List of channels
            subscribe: True to subscribe, False to unsubscribe

        Returns:
            True if sent successfully
        """
        pass

    @abstractmethod
    def _process_message(self, message: Dict[str, Any]):
        """
        Process raw message from WebSocket.
        Must be implemented by exchange-specific subclass.

        Args:
            message: Raw message from exchange
        """
        pass

    @abstractmethod
    def _send_heartbeat(self):
        """
        Send heartbeat/ping to keep connection alive.
        Must be implemented by exchange-specific subclass if needed.
        """
        pass

    def _on_open(self, ws, custom_callback: Optional[Callable] = None):
        """Handle WebSocket connection open"""
        logger.info(f"{self.exchange_name}: WebSocket connected")
        self._set_state(WebSocketState.CONNECTED)
        self._reconnect_attempts = 0
        self._reconnect_delay = self.reconnect_config.initial_delay

        # Send pending subscriptions in batches (BitUnix has a limit of 300
        # channels)
        with self._lock:
            if self._pending_subscriptions:
                # Batch subscriptions to avoid exceeding limits
                batch_size = 250  # Safe margin under 300 limit
                total_subs = len(self._pending_subscriptions)

                for i in range(0, total_subs, batch_size):
                    batch = self._pending_subscriptions[i:i + batch_size]
                    logger.info(
                        f"{
                            self.exchange_name}: Sending batch {
                            i //
                            batch_size +
                            1} with {
                            len(batch)} subscriptions")
                    self._send_subscription_request(batch, True)
                    # Small delay between batches to avoid overwhelming the
                    # server
                    if i + batch_size < total_subs:
                        time.sleep(0.1)

                self._pending_subscriptions.clear()

        # Custom callback
        if custom_callback:
            custom_callback(ws)

    def _on_close(self, ws, code: int, message: str,
                  custom_callback: Optional[Callable] = None):
        """Handle WebSocket connection close"""
        logger.info(
            f"{self.exchange_name}: WebSocket closed - code: {code}, message: {message}")

        self._set_state(WebSocketState.DISCONNECTED)

        # Custom callback
        if custom_callback:
            custom_callback(ws, code, message)

        # Attempt reconnection if configured
        if self._should_reconnect and self.reconnect_config.enabled:
            if self.reconnect_config.max_attempts == - \
                    1 or self._reconnect_attempts < self.reconnect_config.max_attempts:
                self._schedule_reconnect()

    def _on_message_raw(self, ws, message: str):
        """Handle raw WebSocket message"""
        try:
            # Parse JSON message
            data = json.loads(message)

            # Log all messages for debugging
            logger.debug(f"{self.exchange_name}: Received message: {data}")

            # Add to processing queue
            self._message_queue.put(data)

        except json.JSONDecodeError as e:
            logger.error(f"{self.exchange_name}: Failed to parse message: {e}")
            logger.debug(f"Raw message: {message}")
        except Exception as e:
            logger.error(f"{self.exchange_name}: Error handling message: {e}")
            self._handle_error(e)

    def _on_error(self, ws, error: Exception):
        """Handle WebSocket error"""
        logger.error(f"{self.exchange_name}: WebSocket error: {error}")
        self._handle_error(error)
        self._set_state(WebSocketState.ERROR)

    def _on_ping(self, ws, message):
        """Handle ping from server"""
        self._last_ping_time = time.time()
        logger.debug(f"{self.exchange_name}: Received ping")

    def _on_pong(self, ws, message):
        """Handle pong from server"""
        self._last_pong_time = time.time()
        logger.debug(f"{self.exchange_name}: Received pong")

    def _run_websocket(self):
        """Run WebSocket connection in thread"""
        while self._running:
            try:
                if self._ws:
                    logger.info(
                        f"{self.exchange_name}: Starting WebSocket connection")
                    self._ws.run_forever(
                        ping_interval=self._heartbeat_interval,
                        ping_timeout=10
                    )
            except Exception as e:
                logger.error(
                    f"{self.exchange_name}: WebSocket thread error: {e}")
                self._handle_error(e)

            # Wait before potential reconnection
            if self._running:
                time.sleep(1)

    def _process_messages(self):
        """Process messages from queue in separate thread"""
        while self._running:
            try:
                # Get message from queue with timeout
                message = self._message_queue.get(timeout=0.1)

                # Process message
                self._process_message(message)

            except Empty:
                continue
            except Exception as e:
                logger.error(
                    f"{self.exchange_name}: Error processing message: {e}")
                self._handle_error(e)

    def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self._running:
            try:
                if self.is_connected():
                    # Check if we need to send heartbeat
                    current_time = time.time()
                    if current_time - self._last_ping_time > self._heartbeat_interval:
                        self._send_heartbeat()

                time.sleep(5)  # Check every 5 seconds

            except Exception as e:
                logger.error(f"{self.exchange_name}: Heartbeat error: {e}")

    def _schedule_reconnect(self):
        """Schedule reconnection attempt"""
        self._reconnect_attempts += 1
        self._set_state(WebSocketState.RECONNECTING)

        logger.info(
            f"{
                self.exchange_name}: Scheduling reconnection attempt {
                self._reconnect_attempts} in {
                self._reconnect_delay:.1f}s")

        # Schedule reconnection
        timer = threading.Timer(self._reconnect_delay, self._attempt_reconnect)
        timer.daemon = True
        timer.start()

        # Update delay for next attempt
        self._reconnect_delay = min(
            self._reconnect_delay * self.reconnect_config.multiplier,
            self.reconnect_config.max_delay
        )

    def _attempt_reconnect(self):
        """Attempt to reconnect"""
        if not self._running or not self._should_reconnect:
            return

        logger.info(f"{self.exchange_name}: Attempting reconnection")

        # Ensure old threads are cleaned up before reconnecting
        self.disconnect()

        if self._url:
            # Re-enable reconnection and running flags
            self._should_reconnect = True
            self._running = True
            self.connect(self._url)

    def _set_state(self, state: WebSocketState):
        """Set connection state and trigger callback"""
        if self._state != state:
            self._state = state
            if self.on_state_change:
                try:
                    self.on_state_change(state)
                except Exception as e:
                    logger.error(
                        f"{self.exchange_name}: Error in state change callback: {e}")

    def _handle_error(self, error: Exception):
        """Handle error and trigger callback"""
        if self.on_error:
            try:
                self.on_error(error)
            except Exception as e:
                logger.error(
                    f"{self.exchange_name}: Error in error callback: {e}")

    def _create_unified_message(
            self,
            channel: str,
            symbol: Optional[str],
            data: Any) -> WebSocketMessage:
        """Create unified WebSocket message"""
        return WebSocketMessage(
            channel=channel,
            symbol=symbol,
            timestamp=int(time.time() * 1000),
            data=data,
            raw=data if isinstance(data, dict) else None
        )
