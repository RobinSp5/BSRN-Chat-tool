"""
Chat Server - Empfängt eingehende Nachrichten über TCP
Verarbeitet Text- und Bildnachrichten
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
        
    def start(self):
        """Chat Server starten"""
        self.running = True
        
        # TCP Server Socket erstellen
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.settimeout(1)
        
        try:
            # An Chat Port binden
            chat_port = self.config['network']['chat_port']
            self.server_socket.bind(('', chat_port))
            self.server_socket.listen(5)
            
            print(f"Chat Server läuft auf Port {chat_port}")
            
            # Server-Thread starten
            server_thread = threading.Thread(target=self.accept_connections)
            server_thread.daemon = True
            server_thread.start()
            
        except Exception as e:
            print(f"Server Start Error: {e}")
            self.running = False
            
    def stop(self):
        """Chat Server stoppen"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
            
    def accept_connections(self):
        """Eingehende Verbindungen akzeptieren"""
        while self.running:
            try:
                # Neue Verbindungen akzeptieren
                client_socket, addr = self.server_socket.accept()
                
                # Handler-Thread für Client starten
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, addr)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Accept Connection Error: {e}")
                    
    def handle_client(self, client_socket: socket.socket, addr):
        """Client-Verbindung verarbeiten"""
        try:
            # Daten empfangen
            data = b""
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                # Prüfen ob Nachricht vollständig (einfache Lösung)
                try:
                    json.loads(data.decode('utf-8'))
                    break  # Gültiges JSON empfangen
                except:
                    continue  # Weiter Daten sammeln
                    
            if data:
                # JSON-Nachricht dekodieren
                message = json.loads(data.decode('utf-8'))
                self.process_message(message, addr[0])
                
        except Exception as e:
            print(f"Client Handler Error: {e}")
        finally:
            client_socket.close()
            
    def process_message(self, message: Dict[str, Any], sender_ip: str):
        """Empfangene Nachricht verarbeiten"""
        try:
            msg_type = message.get('type', 'unknown')
            sender = message.get('sender', 'Unknown')
            
            if msg_type == 'text':
                # Text-Nachricht verarbeiten
                content = message.get('content', '')
                timestamp = message.get('timestamp', 0)
                
                # Nachricht zur Anzeige weiterleiten
                display_msg = {
                    'type': 'text',
                    'sender': sender,
                    'content': content,
                    'timestamp': timestamp,
                    'sender_ip': sender_ip
                }
                self.ipc_handler.send_message(display_msg)
                
            elif msg_type == 'image':
                # Bild-Nachricht verarbeiten
                image_data = message.get('image_data', '')
                filename = message.get('filename', 'image.jpg')
                timestamp = message.get('timestamp', 0)
                
                # Bild-Nachricht zur Anzeige weiterleiten
                display_msg = {
                    'type': 'image',
                    'sender': sender,
                    'image_data': image_data,
                    'filename': filename,
                    'timestamp': timestamp,
                    'sender_ip': sender_ip
                }
                self.ipc_handler.send_message(display_msg)
                
            elif msg_type == 'system':
                # System-Nachricht (z.B. User joined/left)
                content = message.get('content', '')
                
                display_msg = {
                    'type': 'system',
                    'sender': 'System',
                    'content': content,
                    'timestamp': message.get('timestamp', 0)
                }
                self.ipc_handler.send_message(display_msg)
                
        except Exception as e:
            print(f"Message Processing Error: {e}")
            
    def save_image(self, image_data: str, filename: str) -> str:
        """Base64-kodiertes Bild speichern"""
        try:
            # Base64 dekodieren
            image_bytes = base64.b64decode(image_data)
            
            # Dateiname bereinigen
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            
            # Bild speichern
            with open(f"received_{safe_filename}", 'wb') as f:
                f.write(image_bytes)
                
            return f"received_{safe_filename}"
            
        except Exception as e:
            print(f"Image Save Error: {e}")
            return None
