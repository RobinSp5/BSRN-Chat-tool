"""
Chat Client - Sendet Nachrichten über TCP
Verarbeitet Text- und Bildnachrichten
"""

import socket
import json
import time
import base64
import os
from typing import Dict, Any

class ChatClient:
    # Initialisiert den ChatClient mit Konfiguration und Benutzernamen aus config.toml
    def __init__(self, config: Dict[str, Any], username: str):
        self.config = config
        self.username = username

    # Sendet eine Textnachricht an einen bestimmten Nutzer über TCP
    def send_text_message(self, target_ip: str, target_port: int, message: str) -> bool:
        """Text-Nachricht senden"""
        try:
            msg_data = {
                'type': 'text',
                'sender': self.username,
                'content': message,
                'timestamp': time.time()
            }
            return self.send_message(target_ip, target_port, msg_data)
        except Exception as e:
            print(f"Text Message Error: {e}")
            return False

    # Sendet eine Bildnachricht an einen bestimmten Nutzer über TCP
    def send_image_message(self, target_ip: str, target_port: int, image_path: str) -> bool:
        """Bild-Nachricht senden"""
        try:
            if not os.path.exists(image_path):
                print(f"Bild nicht gefunden: {image_path}")
                return False

            file_size = os.path.getsize(image_path)
            max_size = self.config['user']['max_image_size']
            if file_size > max_size:
                print(f"Bild zu groß: {file_size} bytes (max: {max_size})")
                return False

            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            filename = os.path.basename(image_path)
            msg_data = {
                'type': 'image',
                'sender': self.username,
                'image_data': image_data,
                'filename': filename,
                'timestamp': time.time()
            }

            return self.send_message(target_ip, target_port, msg_data)
        except Exception as e:
            print(f"Image Message Error: {e}")
            return False

    # Sendet eine Systemnachricht an einen bestimmten Nutzer über TCP
    def send_system_message(self, target_ip: str, target_port: int, message: str) -> bool:
        """Systemnachricht senden (z. B. Beenden)"""
        try:
            msg_data = {
                'type': 'system',
                'sender': self.username,
                'content': message,
                'timestamp': time.time()
            }
            return self.send_message(target_ip, target_port, msg_data)
        except Exception as e:
            print(f"System Message Error: {e}")
            return False

    # Sendet eine generische Nachricht über TCP
    def send_message(self, target_ip: str, target_port: int, message_data: Dict[str, Any]) -> bool:
        """TCP-Nachricht senden an IP + Port"""
        client_socket = None
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(self.config['system']['socket_timeout'])
            client_socket.connect((target_ip, target_port))

            message_json = json.dumps(message_data).encode('utf-8')
            client_socket.sendall(message_json)

            return True
        except Exception as e:
            print(f"Send Message Error: {e}")
            return False
        finally:
            if client_socket:
                client_socket.close()

    # Sendet eine Nachricht an alle aktiven Nutzer
    # und gibt die Anzahl der erfolgreichen Sendungen zurück
    def broadcast_message(self, active_users: Dict[str, Any], message: str, msg_type: str = 'text'):
        """Nachricht an alle aktiven Nutzer senden"""
        successful_sends = 0
        total_users = len(active_users)

        for username, user_info in active_users.items():
            target_ip = user_info.get('ip')
            target_port = user_info.get('tcp_port')
            if not target_ip or not target_port:
                continue

            if msg_type == 'text':
                success = self.send_text_message(target_ip, target_port, message)
            elif msg_type == 'image':
                # Bild-Nachrichten nur über CLI aufrufbar
                continue
            else:
                success = self.send_system_message(target_ip, target_port, message)

            if success:
                successful_sends += 1

        return successful_sends, total_users

    # Sendet eine Nachricht an einen bestimmten Nutzer
    def send_to_user(self, username: str, active_users: Dict[str, Any],
                     message: str, msg_type: str = 'text') -> bool:
        """Nachricht an bestimmten Nutzer senden"""
        if username not in active_users:
            print(f"Nutzer '{username}' nicht online")
            return False

        target_ip = active_users[username].get('ip')
        target_port = active_users[username].get('tcp_port')

        if not target_ip or not target_port:
            print(f"IP oder Port für Nutzer '{username}' nicht verfügbar")
            return False

        if msg_type == 'text':
            return self.send_text_message(target_ip, target_port, message)
        elif msg_type == 'image':
            return self.send_image_message(target_ip, target_port, message)
        else:
            return self.send_system_message(target_ip, target_port, message)