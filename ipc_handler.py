"""
Simple Inter-Process Communication Handler
Verwaltet Queues für Nachrichten zwischen den Modulen
"""

import queue
import threading
from typing import Dict, Any

class IPCHandler:
    def __init__(self):
        # Verschiedene Queues für unterschiedliche Nachrichtentypen
        self.message_queue = queue.Queue()      # Eingehende Chat-Nachrichten
        self.discovery_queue = queue.Queue()    # Discovery-Updates
        self.outgoing_queue = queue.Queue()     # Ausgehende Nachrichten
        self.user_list_queue = queue.Queue()    # Aktive Nutzer
        self.command_queue = queue.Queue()      # CLI-Befehle
        
        # Thread-Lock für sichere Operationen
        self.lock = threading.Lock()
        self.active_users = {}  # Dict mit aktiven Nutzern
        
    def send_message(self, message: Dict[str, Any]):
        """Chat-Nachricht zur Verarbeitung einreihen"""
        self.message_queue.put(message)
        
    def get_message(self, timeout=1):
        """Chat-Nachricht aus Queue holen"""
        try:
            return self.message_queue.get(timeout=timeout)
        except queue.Empty:
            return None
            
    def send_discovery_update(self, user_info: Dict[str, Any]):
        """Discovery-Update senden"""
        self.discovery_queue.put(user_info)
        
    def get_discovery_update(self, timeout=1):
        """Discovery-Update holen"""
        try:
            return self.discovery_queue.get(timeout=timeout)
        except queue.Empty:
            return None
            
    def add_outgoing_message(self, target_ip: str, message: Dict[str, Any]):
        """Ausgehende Nachricht einreihen"""
        self.outgoing_queue.put((target_ip, message))
        
    def get_outgoing_message(self, timeout=1):
        """Ausgehende Nachricht holen"""
        try:
            return self.outgoing_queue.get(timeout=timeout)
        except queue.Empty:
            return None
            
    def update_user_list(self, username: str, ip_address: str, status: str = "online"):
        """Nutzerliste aktualisieren"""
        with self.lock:
            self.active_users[username] = {
                'ip': ip_address,
                'status': status,
                'last_seen': __import__('time').time()
            }
            
    def get_active_users(self):
        """Aktive Nutzerliste zurückgeben"""
        with self.lock:
            return self.active_users.copy()
            
    def remove_user(self, username: str):
        """Nutzer aus aktiver Liste entfernen"""
        with self.lock:
            if username in self.active_users:
                del self.active_users[username]
                
    def cleanup_inactive_users(self, timeout=60):
        """Inaktive Nutzer nach Timeout entfernen"""
        current_time = __import__('time').time()
        with self.lock:
            inactive_users = []
            for username, info in self.active_users.items():
                if current_time - info['last_seen'] > timeout:
                    inactive_users.append(username)
            
            for username in inactive_users:
                del self.active_users[username]
