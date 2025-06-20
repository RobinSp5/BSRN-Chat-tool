import sys
import argparse
import time
import signal
import threading
import os
import socket
import toml

from ipc_handler import IPCHandler
from discovery import DiscoveryService
from chat_server import ChatServer
from chat_client import ChatClient
from cli import CLI 


class SimpleChatApp:
    # Hauptklasse für die SLCP Chat-Anwendung
    # Initialisiert die Konfiguration, IPC-Handler, Chat-Server und Discovery-Service
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

    # Ermittelt die lokale IP-Adresse des Systems
    # Via UDP-Verbindung zu einem externen Server
    # in diesem Fall zu Google DNS
    def get_local_ip(self) -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80)) #8.8.8.8 = Google DNS
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip # Rückgabe der lokalen IP-Adresse

    # Lädt die Konfiguration aus der angegebenen TOML-Datei
    def load_config(self, path: str) -> dict:
        if not os.path.exists(path):
            # Wenn die Datei nicht existiert, Fehlermeldung ausgeben und beenden
            print(f"config.toml nicht gefunden unter {path}.")
            sys.exit(1)

        try:
            with open(path, 'r', encoding='utf-8') as f:
                return toml.load(f) # Lädt die Konfiguration aus der TOML-Datei
            
        # Wenn ein Fehler beim Laden der Datei auftritt, Fehlermeldung ausgeben und beenden
        except Exception as e:
            print(f"Fehler beim Laden von config.toml: {e}")
            sys.exit(1)

    # Startet die Anwendung und initialisiert den Chat-Server und Discovery-Service
    def start(self):
        self.running = True
        self.discovery.start() # Startet den Discovery-Service

        print(f"[SLCP] Starte Peer-to-Peer Chat...")
        print(f"[Server] Lauscht auf TCP-Port {self.config['network']['chat_port']}")
        print(f"[Hinweis] Tippe /join <name>, um dem Chat beizutreten.\n")

        threading.Thread(target=self.cleanup_loop, daemon=True).start()
        self.cli.start() # Startet die CLI
        #self.shutdown() #unnoetig?!

    # Periodisch inaktiv Nutzer entfernen
    def cleanup_loop(self):
        while self.running:
            try:
                self.ipc_handler.cleanup_inactive_users(60)
                time.sleep(30) # Warte 30 Sekunden vor der nächsten Bereinigung
            except Exception:
                pass

    # Beendet die Anwendung, stoppt den Chat-Server und Discovery-Service
    def shutdown(self):
        print("\nChat wird beendet...")
        self.running = False
        self.cli.stop()
        self.chat_server.stop()
        self.discovery.stop()
        print("Anwendung beendet.")

    # Signal-Handler für STRG+C --> sauberes beenden der Anwendung
    # Programm beendet sich sauber, wenn STRG+C gedrückt wird
    # und ruft die shutdown-Methode auf
    def signal_handler(self, signum, frame):
        print("\n[STRG+C] Unterbrechung erkannt – beende...")
        self.shutdown()
        sys.exit(0)


# Funktion zum Parsen der Kommandozeilenargumente
def parse_arguments():
    parser = argparse.ArgumentParser(description="SLCP Chat-Client")
    parser.add_argument("-c", "--config", default="config.toml", help="Pfad zur config.toml")
    return parser.parse_args()

# Hauptfunktion, die die Anwendung startet
def main():
    args = parse_arguments()
    print("[SLCP] Client wird gestartet...\n")
    app = SimpleChatApp(config_path=args.config, username="")
    app.start()

# Warten auf Beendigung der Anwendung
if __name__ == "__main__":
    main()
