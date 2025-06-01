"""
Simple Inter-Process Communication Handler
Verwaltet Queues für Nachrichten zwischen den Modulen
"""

import queue
import threading
import time
from typing import Dict, Any

class IPCHandler:
    def __init__(self):
        # Queues für verschiedene Kommunikationstypen
        self.message_queue = queue.Queue()      # Eingehende Nachrichten
        self.discovery_queue = queue.Queue()    # Discovery-Updates
        self.outgoing_queue = queue.Queue()     # Ausgehende Nachrichten
        self.user_list_queue = queue.Queue()    # Nutzerliste (optional)
        self.command_queue = queue.Queue()      # CLI-Kommandos

        # Nutzerverwaltung
        self.lock = threading.Lock()
        self.active_users = {}  # {username: {'ip': ..., 'tcp_port': ..., 'status': ..., 'last_seen': ...}}

    def send_message(self, message: Dict[str, Any]):
        """Chat-Nachricht zur Verarbeitung einreihen"""
        self.message_queue.put(message)

    def get_message(self, timeout=1):
        """Chat-Nachricht abrufen"""
        try:
            return self.message_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def send_discovery_update(self, user_info: Dict[str, Any]):
        """Discovery-Update einreihen"""
        self.discovery_queue.put(user_info)

    def get_discovery_update(self, timeout=1):
        """Discovery-Update abrufen"""
        try:
            return self.discovery_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def add_outgoing_message(self, target_ip: str, message: Dict[str, Any]):
        """Ausgehende Nachricht einreihen"""
        self.outgoing_queue.put((target_ip, message))

    def get_outgoing_message(self, timeout=1):
        """Ausgehende Nachricht abrufen"""
        try:
            return self.outgoing_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def update_user_list(self, username: str, ip_address: str, tcp_port: int, timestamp: float = None):
        """Nutzerliste aktualisieren und TCP-Port speichern"""
        if timestamp is None:
            timestamp = time.time()
        with self.lock:
            self.active_users[username] = {
                'ip': ip_address,
                'tcp_port': tcp_port,
                'status': 'online',
                'last_seen': timestamp
            }

    def get_active_users(self):
        """Aktive Nutzerliste abrufen"""
        with self.lock:
            return self.active_users.copy()

    def remove_user(self, username: str):
        """Nutzer aus Liste entfernen"""
        with self.lock:
            if username in self.active_users:
                del self.active_users[username]

    def remove_user_by_name(self, username: str):
        """Alias für remove_user, für Kompatibilität im Servercode"""
        self.remove_user(username)

    def cleanup_inactive_users(self, timeout=60):
        """Inaktive Nutzer nach Timeout entfernen"""
        current_time = time.time()
        with self.lock:
            inactive_users = []
            for username, info in self.active_users.items():
                if current_time - info['last_seen'] > timeout:
                    inactive_users.append(username)

            for username in inactive_users:
                del self.active_users[username]
