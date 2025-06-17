import queue
import threading
import time
from typing import Dict, Any


class IPCHandler:
    def __init__(self):
        self.message_queue = queue.Queue()
        self.discovery_queue = queue.Queue()
        self.lock = threading.Lock()
        self.active_users = {}
        self.self_visible = True

    def send_message(self, message: Dict[str, Any]):
        self.message_queue.put(message)

    def get_message(self, timeout=1):
        try:
            return self.message_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def send_discovery_update(self, user_info: Dict[str, Any]):
        self.discovery_queue.put(user_info)

    def get_discovery_update(self, timeout=1):
        try:
            return self.discovery_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def update_user_list(self, username: str, ip_address: str, tcp_port: int, timestamp: float = None):
        if not username.strip():  # LEERE ODER UNGÜLTIGE NAMEN IGNORIEREN
            return
        if timestamp is None:
            timestamp = time.time()
        with self.lock:
            self.active_users[username] = {
                'ip': ip_address,
                'tcp_port': tcp_port,
                'status': 'online',
                'last_seen': timestamp,
                'visible': True
            }

    def get_active_users(self, only_visible=True):
        with self.lock:
            result = {}
            for name, info in self.active_users.items():
                if not only_visible or info.get('visible', True):
                    result[name] = info
            return result

    def set_visibility(self, visible: bool):
        with self.lock:
            self.self_visible = visible

    def is_visible(self) -> bool:
        with self.lock:
            return self.self_visible

    def remove_user(self, username: str):
        with self.lock:
            if username in self.active_users:
                del self.active_users[username]

    def remove_user_by_name(self, username: str):
        self.remove_user(username)

    def cleanup_inactive_users(self, timeout=60):
        current_time = time.time()
        with self.lock:
            to_remove = []
            for username, info in self.active_users.items():
                if current_time - info['last_seen'] > timeout:
                    to_remove.append(username)
            for name in to_remove:
                del self.active_users[name]