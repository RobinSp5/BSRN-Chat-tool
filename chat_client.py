import socket
import os
from typing import Dict, Any


class ChatClient:
    def __init__(self, config: Dict[str, Any], username: str):
        self.config = config
        self.username = username

    # Sendet eine SLCP-Nachricht über TCP
    def send_text_message(self, target_ip: str, target_port: int, target_handle: str, message: str) -> bool:
        """Sendet eine SLCP-Textnachricht über TCP (max. 512 Bytes inklusive Header)"""
        try:
            slcp_line = f"MSG {target_handle} {message}\n"
            encoded = slcp_line.encode("utf-8")

            if len(encoded) > 512:
                print(f"Nachricht zu lang ({len(encoded)} Bytes). Maximal erlaubt: 512 Bytes.")
                return False

            with socket.create_connection((target_ip, target_port), timeout=self.config['system']['socket_timeout']) as sock:
                sock.sendall(encoded)
            return True
        except Exception as e:
            print(f"Text Message Error: {e}")
            return False

    # Sendet eine SLCP-Bildnachricht über TCP
    def send_image_message(self, target_ip: str, target_port: int, target_handle: str, image_path: str) -> bool:
        """Sendet eine SLCP-Bildnachricht über TCP"""
        try:
            if not os.path.exists(image_path):
                print(f"Bild nicht gefunden: {image_path}")
                return False

            file_size = os.path.getsize(image_path)
            max_size = self.config['user']['max_image_size']
            if file_size > max_size:
                print(f"Bild zu groß: {file_size} bytes (max: {max_size})")
                return False

            slcp_header = f"IMG {target_handle} {file_size}\n"

            with open(image_path, "rb") as f:
                image_data = f.read()

            with socket.create_connection((target_ip, target_port), timeout=self.config['system']['socket_timeout']) as sock:
                sock.sendall(slcp_header.encode("utf-8"))
                sock.sendall(image_data)

            return True
        except Exception as e:
            print(f"Image Message Error: {e}")
            return False

