#!/usr/bin/env python3
"""
SSG Sender: WebSocket client for streaming SSG commands to ESP32
Implements sliding window protocol with acks, retries, and telemetry

Design Doc Section 6.4 (Device Streamer)
"""

import asyncio
import websockets
import json
import time
from typing import List, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

import config


@dataclass
class CommandStatus:
    """Track status of in-flight command"""
    seq: int
    line: str
    sent_time: float
    retry_count: int = 0


class SSGSender:
    """WebSocket client for streaming SSG commands with sliding window protocol"""
    
    def __init__(self, esp32_ip: str = None):
        self.esp32_ip = esp32_ip or config.ESP32_IP
        self.uri = f"ws://{self.esp32_ip}:{config.ESP32_PORT}{config.WEBSOCKET_PATH}"
        self.websocket = None
        
        # Sliding window state
        self.in_flight: dict[int, CommandStatus] = {}
        self.next_seq_to_send = 1
        self.last_acked_seq = 0
        
        # Statistics
        self.total_sent = 0
        self.total_acked = 0
        self.total_retries = 0
        self.start_time = None
        
        # Callbacks
        self.on_telemetry: Optional[Callable] = None
        self.on_status: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_progress: Optional[Callable] = None
        
        # Control flags
        self.is_connected = False
        self.is_streaming = False
        self.should_stop = False
    
    async def connect(self) -> bool:
        """Connect to ESP32 WebSocket"""
        try:
            print(f"Connecting to {self.uri}...")
            self.websocket = await websockets.connect(self.uri)
            self.is_connected = True
            print("Connected!")
            
            # Request initial status
            await self.websocket.send("N0 M408")
            
            return True
            
        except Exception as e:
            print(f"Connection failed: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from ESP32"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            print("Disconnected")
    
    async def stream_ssg_file(self, filepath: str) -> bool:
        """
        Stream an SSG file to the ESP32
        
        Args:
            filepath: Path to .ssg file
            
        Returns:
            True if successful, False otherwise
        """
        # Load SSG commands
        ssg_lines = Path(filepath).read_text().strip().split('\n')
        ssg_lines = [line.strip() for line in ssg_lines if line.strip()]
        
        print(f"Loaded {len(ssg_lines)} commands from {filepath}")
        
        return await self.stream_commands(ssg_lines)
    
    async def stream_commands(self, commands: List[str]) -> bool:
        """
        Stream a list of SSG commands to ESP32
        
        Args:
            commands: List of SSG command strings
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            print("ERROR: Not connected to ESP32")
            return False
        
        self.is_streaming = True
        self.should_stop = False
        self.start_time = time.time()
        self.total_sent = 0
        self.total_acked = 0
        self.total_retries = 0
        
        total_commands = len(commands)
        commands_to_send = list(commands)
        
        print(f"\nStreaming {total_commands} commands...")
        print(f"Window size: {config.WINDOW_SIZE}")
        print(f"Ack timeout: {config.ACK_TIMEOUT_SEC}s")
        print("="*60)
        
        try:
            # Start receiver task
            receiver_task = asyncio.create_task(self._receive_loop())
            
            # Streaming loop
            while commands_to_send or self.in_flight:
                # Check for stop signal
                if self.should_stop:
                    print("\nStreaming stopped by user")
                    break
                
                # Send commands up to window size
                while len(self.in_flight) < config.WINDOW_SIZE and commands_to_send:
                    cmd = commands_to_send.pop(0)
                    await self._send_command(cmd)
                
                # Check for timeouts and retry
                await self._check_timeouts()
                
                # Progress update
                if self.on_progress:
                    progress = self.total_acked / total_commands if total_commands > 0 else 0
                    self.on_progress(progress, self.total_acked, total_commands)
                
                # Small delay to prevent busy loop
                await asyncio.sleep(0.01)
            
            # Wait for all acks
            print("\nWaiting for final acknowledgements...")
            timeout = time.time() + 5.0
            while self.in_flight and time.time() < timeout:
                await self._check_timeouts()
                await asyncio.sleep(0.1)
            
            # Cancel receiver
            receiver_task.cancel()
            
            # Final statistics
            elapsed = time.time() - self.start_time
            self._print_statistics(elapsed)
            
            success = len(self.in_flight) == 0 and not self.should_stop
            
            if success:
                print("\n✅ Streaming completed successfully!")
            else:
                print("\n❌ Streaming incomplete")
                print(f"Commands still in flight: {len(self.in_flight)}")
            
            self.is_streaming = False
            return success
            
        except Exception as e:
            print(f"\nERROR during streaming: {e}")
            self.is_streaming = False
            return False
    
    async def _send_command(self, cmd: str):
        """Send a command and track it"""
        # Extract sequence number (should already be in format "N123 ...")
        # If not, this is an error
        if not cmd.startswith('N'):
            print(f"WARNING: Command missing sequence number: {cmd}")
            return
        
        # Parse sequence number
        parts = cmd.split(' ', 1)
        seq_str = parts[0][1:]  # Remove 'N'
        try:
            seq = int(seq_str)
        except ValueError:
            print(f"WARNING: Invalid sequence number: {cmd}")
            return
        
        # Send command
        await self.websocket.send(cmd)
        
        # Track in flight
        self.in_flight[seq] = CommandStatus(
            seq=seq,
            line=cmd,
            sent_time=time.time()
        )
        
        self.total_sent += 1
    
    async def _receive_loop(self):
        """Receive and handle responses from ESP32"""
        try:
            async for message in self.websocket:
                await self._handle_response(message)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Receiver error: {e}")
    
    async def _handle_response(self, message: str):
        """Handle a response from ESP32"""
        message = message.strip()
        
        # Parse response type
        if message.startswith("ok"):
            # Ack: "ok N123"
            parts = message.split()
            if len(parts) >= 2 and parts[1].startswith('N'):
                seq = int(parts[1][1:])
                self._handle_ack(seq)
        
        elif message.startswith("err"):
            # Error: "err N123 code=LIMIT"
            print(f"\n⚠️  ESP32 Error: {message}")
            if self.on_error:
                self.on_error(message)
        
        elif message.startswith("busy"):
            # Busy: "busy q=32 state=PRINTING"
            # Just wait, don't send more
            pass
        
        elif message.startswith("telemetry"):
            # Telemetry: "telemetry {...json...}"
            try:
                json_str = message.split(' ', 1)[1]
                data = json.loads(json_str)
                if self.on_telemetry:
                    self.on_telemetry(data)
            except Exception as e:
                print(f"Failed to parse telemetry: {e}")
        
        elif message.startswith("status"):
            # Status: "status state=READY q=0 ..."
            if self.on_status:
                self.on_status(message)
        
        elif message.startswith("pos"):
            # Position report: "pos X:10.00 Y:20.00"
            pass  # Just informational
    
    def _handle_ack(self, seq: int):
        """Handle acknowledgement of command"""
        if seq in self.in_flight:
            del self.in_flight[seq]
            self.total_acked += 1
            self.last_acked_seq = max(self.last_acked_seq, seq)
    
    async def _check_timeouts(self):
        """Check for timed-out commands and retry"""
        now = time.time()
        
        for seq, status in list(self.in_flight.items()):
            if now - status.sent_time > config.ACK_TIMEOUT_SEC:
                # Timeout - retry
                if status.retry_count < config.MAX_RETRIES:
                    print(f"\n⏱️  Timeout N{seq}, retrying ({status.retry_count + 1}/{config.MAX_RETRIES})")
                    status.retry_count += 1
                    status.sent_time = now
                    await self.websocket.send(status.line)
                    self.total_retries += 1
                else:
                    print(f"\n❌ Max retries exceeded for N{seq}")
                    del self.in_flight[seq]
                    if self.on_error:
                        self.on_error(f"Max retries exceeded: N{seq}")
    
    def _print_statistics(self, elapsed: float):
        """Print streaming statistics"""
        print("\n" + "="*60)
        print("STREAMING STATISTICS")
        print("="*60)
        print(f"Total sent: {self.total_sent}")
        print(f"Total acked: {self.total_acked}")
        print(f"Total retries: {self.total_retries}")
        print(f"Success rate: {100*self.total_acked/self.total_sent:.1f}%" if self.total_sent > 0 else "N/A")
        print(f"Elapsed time: {elapsed:.1f}s")
        print(f"Throughput: {self.total_acked/elapsed:.1f} commands/sec" if elapsed > 0 else "N/A")
    
    def stop(self):
        """Stop streaming"""
        self.should_stop = True
    
    async def send_home(self):
        """Send homing command"""
        if not self.is_connected:
            return False
        await self.websocket.send("N0 G28")
        return True
    
    async def send_pause(self):
        """Pause printing (turn sauce off)"""
        if not self.is_connected:
            return False
        await self.websocket.send("N0 M5")
        return True
    
    async def request_status(self):
        """Request status from ESP32"""
        if not self.is_connected:
            return False
        await self.websocket.send("N0 M408")
        return True


# ============================================
# CLI INTERFACE
# ============================================

async def main():
    """Command-line interface for SSG sender"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Stream SSG commands to ESP32 plotter")
    parser.add_argument("ssg_file", help="Path to .ssg file")
    parser.add_argument("--ip", help="ESP32 IP address", default=config.ESP32_IP)
    parser.add_argument("--home-first", action="store_true", help="Send G28 before streaming")
    
    args = parser.parse_args()
    
    # Create sender
    sender = SSGSender(esp32_ip=args.ip)
    
    # Set up callbacks
    def on_telemetry(data):
        pos = data.get('pos', {})
        print(f"  Position: X={pos.get('x', 0):.2f} Y={pos.get('y', 0):.2f} | Queue: {data.get('q', 0)}", end='\r')
    
    def on_error(msg):
        print(f"\n❌ Error: {msg}")
    
    def on_progress(progress, acked, total):
        bar_length = 40
        filled = int(bar_length * progress)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"\r[{bar}] {progress*100:.1f}% ({acked}/{total})", end='')
    
    sender.on_telemetry = on_telemetry
    sender.on_error = on_error
    sender.on_progress = on_progress
    
    # Connect
    if not await sender.connect():
        print("Failed to connect to ESP32")
        return 1
    
    # Home if requested
    if args.home_first:
        print("Sending homing command...")
        await sender.send_home()
        await asyncio.sleep(10)  # Wait for homing to complete
    
    # Stream file
    success = await sender.stream_ssg_file(args.ssg_file)
    
    # Disconnect
    await sender.disconnect()
    
    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)

