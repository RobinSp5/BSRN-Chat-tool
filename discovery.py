import socket
import threading
import time
from typing import Dict, Any


class DiscoveryService:
    def __init__(self, config: Dict[str, Any], ipc_handler, username: str, chat_tcp_port: int):
        self.config = config
        self.ipc_handler = ipc_handler
        self.username = username
        self.chat_tcp_port = chat_tcp_port
        self.running = False

        self.broadcast_ip = self.config["network"].get("broadcast_address", "255.255.255.255")
        self.discovery_port = self.config["network"].get("whoisport", 4000)

        # UDP-Socket für Broadcasts
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass
        self.listen_socket.settimeout(1)

    def start(self):
        self.running = True
        try:
            self.listen_socket.bind(('', self.discovery_port))
            threading.Thread(target=self.listen_loop, daemon=True).start()
            print(f"[Discovery] ✅ UDP-Listener aktiv (Port {self.discovery_port}).")
        except OSError:
            print(f"[Discovery] ⚠️ Port {self.discovery_port} belegt – kein Listener aktiv.")
        self.send_join()

    def stop(self):
        self.running = False
        self.send_leave()
        try:
            self.listen_socket.close()
        except Exception:
            pass

    def listen_loop(self):
        while self.running:
            try:
                data, addr = self.listen_socket.recvfrom(1024)
                message = data.decode('utf-8', errors='ignore').strip()
                self.handle_message(message, addr[0])
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[Discovery] Empfangsfehler: {e}")

    def handle_message(self, message: str, sender_ip: str):
        if message.startswith("JOIN"):
            parts = message.split(" ")
            if len(parts) == 3:
                peer, port = parts[1], int(parts[2])
                if peer != self.username:
                    self.ipc_handler.update_user_list(peer, sender_ip, port, time.time())

        elif message.startswith("LEAVE"):
            parts = message.split(" ")
            if len(parts) == 2:
                peer = parts[1]
                if peer != self.username:
                    self.ipc_handler.remove_user_by_name(peer)

        elif message == "WHO":
            self.send_knowusers(sender_ip)

        elif message.startswith("KNOWUSERS"):
            payload = message[10:]
            for chunk in payload.split(","):
                parts = chunk.strip().split(" ")
                if len(parts) == 3:
                    peer, ip, port = parts[0], parts[1], int(parts[2])
                    if peer != self.username:
                        self.ipc_handler.update_user_list(peer, ip, port, time.time())

    def send_udp_broadcast(self, text: str):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto((text + "\n").encode('utf-8'),
                     (self.broadcast_ip, self.discovery_port))

    def send_join(self):
        self.send_udp_broadcast(f"JOIN {self.username} {self.chat_tcp_port}")

    def send_leave(self):
        self.send_udp_broadcast(f"LEAVE {self.username}")

    def request_discovery(self):
        # Sende zuerst JOIN, damit alle dich kennen, dann WHO
        self.send_join()
        time.sleep(0.1)  # kleine Verzögerung, damit JOIN verarbeitet wird
        self.send_udp_broadcast("WHO")

    def send_knowusers(self, target_ip: str):
        users = self.ipc_handler.get_active_users(only_visible=True)
        if not users:
            return

        parts = [f"{u} {info['ip']} {info['tcp_port']}" for u, info in users.items()]
        msg = "KNOWUSERS " + ", ".join(parts) + "\n"

        target_port = self.chat_tcp_port
        for info in self.ipc_handler.get_active_users(only_visible=False).values():
            if info['ip'] == target_ip:
                target_port = info['tcp_port']
                break

        try:
            with socket.create_connection(
                (target_ip, target_port),
                timeout=self.config['system']['socket_timeout']
            ) as sock:
                sock.sendall(msg.encode('utf-8'))
        except Exception as e:
            print(f"[Discovery] Fehler beim Senden von KNOWUSERS an {target_ip}:{target_port}: {e}")