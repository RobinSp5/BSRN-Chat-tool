"""
Chat Server - Empfängt eingehende Nachrichten über TCP
Verarbeitet Text- und Bildnachrichten (Base64)
"""

import socket
import threading
import json
import base64
from typing import Dict, Any

class ChatServer:
    def __init__(self, config: Dict[str, Any], ipc_handler):
        self.config = config
        self.ipc_handler = ipc_handler
        self.running = False
        self.server_socket = None

    def get_free_tcp_port(self) -> int:
        """Wähle automatisch einen freien TCP-Port vom OS"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    def start(self):
        """Chat Server starten"""
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.settimeout(1)

        try:
            configured_port = self.config['network'].get('chat_port', 0)

            # Wenn Port 0 oder belegt → freien Port wählen
            try:
                self.server_socket.bind(('', configured_port))
            except OSError:
                print(f"⚠️ Port {configured_port} belegt – freier Port wird verwendet.")
                configured_port = self.get_free_tcp_port()
                self.server_socket.bind(('', configured_port))

            self.config['network']['chat_port'] = configured_port
            self.server_socket.listen(5)

            print(f"✅ Chat Server läuft auf Port {configured_port}")

            server_thread = threading.Thread(target=self.accept_connections)
            server_thread.daemon = True
            server_thread.start()

        except Exception as e:
            print(f"❌ Server Start Error: {e}")
            self.running = False

    def stop(self):
        """Server stoppen"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()

    def accept_connections(self):
        """Neue Verbindungen annehmen"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"❌ Accept Connection Error: {e}")

    def handle_client(self, client_socket: socket.socket, addr):
        """Nachricht eines verbundenen Clients empfangen"""
        try:
            data = b""
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                try:
                    json.loads(data.decode('utf-8'))
                    break
                except:
                    continue

            if data:
                message = json.loads(data.decode('utf-8'))
                self.process_message(message, addr[0])

        except Exception as e:
            print(f"❌ Client Handler Error: {e}")
        finally:
            client_socket.close()

    def process_message(self, message: Dict[str, Any], sender_ip: str):
        """Verarbeite empfangene Nachricht"""
        try:
            msg_type = message.get('type', 'unknown')
            sender = message.get('sender', 'Unknown')

            if msg_type == 'text':
                display_msg = {
                    'type': 'text',
                    'sender': sender,
                    'content': message.get('content', ''),
                    'timestamp': message.get('timestamp', 0),
                    'sender_ip': sender_ip
                }
                self.ipc_handler.send_message(display_msg)

            elif msg_type == 'image':
                display_msg = {
                    'type': 'image',
                    'sender': sender,
                    'image_data': message.get('image_data', ''),
                    'filename': message.get('filename', 'image.jpg'),
                    'timestamp': message.get('timestamp', 0),
                    'sender_ip': sender_ip
                }
                self.ipc_handler.send_message(display_msg)

            elif msg_type == 'system':
                content = message.get('content', '').lower()

                # Prüfen ob es eine Verabschiedung ist → dann sofort entfernen
                if "hat den chat verlassen" in content:
                    self.ipc_handler.remove_user_by_name(sender)

                display_msg = {
                    'type': 'system',
                    'sender': 'System',
                    'content': message.get('content', ''),
                    'timestamp': message.get('timestamp', 0)
                }
                self.ipc_handler.send_message(display_msg)

        except Exception as e:
            print(f"❌ Message Processing Error: {e}")

    def save_image(self, image_data: str, filename: str) -> str:
        """Bild aus Base64 speichern"""
        try:
            image_bytes = base64.b64decode(image_data)
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            filepath = f"received_{safe_filename}"
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            return filepath
        except Exception as e:
            print(f"❌ Image Save Error: {e}")
            return None
