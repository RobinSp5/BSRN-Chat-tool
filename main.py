import sys
import argparse
import time
import signal
import threading
import os
import socket

try:
    import toml
except ImportError:
    print("TOML nicht installiert – bitte mit `pip install toml` installieren")
    sys.exit(1)

from ipc_handler import IPCHandler
from discovery import DiscoveryService
from chat_server import ChatServer
from chat_client import ChatClient
from cli import CLI 


class SimpleChatApp:
    def __init__(self, config_path="config.toml", username=""):
        self.config = self.load_config(config_path)
        self.username = username

        # Lokale IP ermitteln und in Config speichern
        self.config['network']['local_ip'] = self.get_local_ip()

        self.ipc_handler = IPCHandler()
        self.chat_server = ChatServer(self.config, self.ipc_handler)
        self.chat_server.start()

        chat_port = self.chat_server.config["network"]["chat_port"]

        self.discovery = DiscoveryService(self.config, self.ipc_handler, self.username, chat_port)
        self.chat_client = ChatClient(self.config, self.username)
        self.cli = CLI(self.config, self.ipc_handler, self.chat_client, self.discovery)

        self.running = False
        signal.signal(signal.SIGINT, self.signal_handler)

    def get_local_ip(self) -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def load_config(self, path: str) -> dict:
        if not os.path.exists(path):
            print(f"config.toml nicht gefunden unter {path}.")
            sys.exit(1)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return toml.load(f)
        except Exception as e:
            print(f"Fehler beim Laden von config.toml: {e}")
            sys.exit(1)

    def start(self):
        self.running = True
        self.discovery.start()

        print(f"[SLCP] Starte Peer-to-Peer Chat...")
        print(f"[Server] Lauscht auf TCP-Port {self.config['network']['chat_port']}")
        print(f"[Hinweis] Tippe /join <name>, um dem Chat beizutreten.\n")

        threading.Thread(target=self.cleanup_loop, daemon=True).start()
        self.cli.start()
        self.shutdown()

    def cleanup_loop(self):
        while self.running:
            try:
                self.ipc_handler.cleanup_inactive_users(60)
                time.sleep(30)
            except Exception:
                pass

    def shutdown(self):
        print("\nChat wird beendet...")
        self.running = False
        self.cli.stop()
        self.chat_server.stop()
        self.discovery.stop()
        print("Anwendung beendet.")

    def signal_handler(self, signum, frame):
        print("\n[STRG+C] Unterbrechung erkannt – beende...")
        self.shutdown()
        sys.exit(0)


def parse_arguments():
    parser = argparse.ArgumentParser(description="SLCP Chat-Client")
    parser.add_argument("-c", "--config", default="config.toml", help="Pfad zur config.toml")
    return parser.parse_args()


def main():
    args = parse_arguments()
    print("[SLCP] Client wird gestartet...\n")
    app = SimpleChatApp(config_path=args.config, username="")
    app.start()


if __name__ == "__main__":
    main()
