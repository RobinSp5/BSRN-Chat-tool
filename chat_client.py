import socket
import os
from typing import Dict, Any


class ChatClient:
    # Konstruktor der ChatClient-Klasse
    def __init__(self, config: Dict[str, Any], username: str):
        self.config = config
        self.username = username

    # Sendet eine SLCP-Nachricht über TCP
    def send_text_message(self, target_ip: str, target_port: int, target_handle: str, message: str) -> bool:
        try:
            # Prüfen, ob die Nachricht leer ist
            slcp_line = f"MSG {target_handle} {message}\n"
            encoded = slcp_line.encode("utf-8")

            # Prüfen, ob die Nachricht zu lang ist (maximal 512 Bytes)
            if len(encoded) > 512:
                print(f"Nachricht zu lang ({len(encoded)} Bytes). Maximal erlaubt: 512 Bytes.")
                return False

            
            with socket.create_connection((target_ip, target_port), timeout=self.config['system']['socket_timeout']) as sock:
                sock.sendall(encoded) # Sende die SLCP-Nachricht
            return True
        #Error-Handling
        except Exception as e:
            print(f"Text Message Error: {e}")
            return False

    # Sendet eine SLCP-Bildnachricht über TCP
    def send_image_message(self, target_ip: str, target_port: int, target_handle: str, image_path: str) -> bool:
        """Sendet eine SLCP-Bildnachricht über TCP"""
        try:
            # Prüfen, ob der Pfad zu einem Bild existiert
            if not os.path.exists(image_path):
                print(f"Bild nicht gefunden: {image_path}")
                return False

            file_size = os.path.getsize(image_path) # Größe des Bildes in Bytes
            max_size = self.config['user']['max_image_size'] # Maximale Bildgröße in Bytes auss config auslesen
            # Prüfen, ob die Bildgröße das Limit überschreitet
            if file_size > max_size:
                print(f"Bild zu groß: {file_size} bytes (max: {max_size})")
                return False

            slcp_header = f"IMG {target_handle} {file_size}\n"

            with open(image_path, "rb") as f:
                image_data = f.read()

            # Stellt eine TCP-Verbindung zum Zielnutzer her und überträgt zuerst den SLCP-Header, dann die Bilddaten.
            with socket.create_connection((target_ip, target_port), timeout=self.config['system']['socket_timeout']) as sock:
                sock.sendall(slcp_header.encode("utf-8"))
                sock.sendall(image_data)

            return True
        #Error-Handling
        except Exception as e:
            print(f"Image Message Error: {e}")
            return False

