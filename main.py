"""
Simple Local Chat Protocol (SLCP) - Hauptprogramm
Dezentrales Chat-System für lokale Netzwerke
"""

import sys
import argparse
import time
import signal
import threading
try:
    import toml
except ImportError:
    print("TOML-Bibliothek fehlt. Installieren Sie mit: pip install toml")
    sys.exit(1)

# Import der eigenen Module
from ipc_handler import IPCHandler
from discovery import DiscoveryService
from chat_server import ChatServer
from chat_client import ChatClient
from cli import CLI

class SimpleChatApp:
    def __init__(self, config_path="config.toml", username=None):
        # Konfiguration laden
        self.config = self.load_config(config_path)
        
        # Nutzername setzen
        self.username = username or self.config['user']['default_username']
        
        # Kernkomponenten initialisieren
        self.ipc_handler = IPCHandler()
        self.discovery_service = DiscoveryService(self.config, self.ipc_handler, self.username)
        self.chat_server = ChatServer(self.config, self.ipc_handler)
        self.chat_client = ChatClient(self.config, self.username)
        self.cli = CLI(self.config, self.ipc_handler, self.chat_client, self.discovery_service)
        
        # Shutdown-Handler
        self.running = False
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def load_config(self, config_path: str) -> dict:
        """Konfigurationsdatei laden"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = toml.load(f)
            print(f"Konfiguration geladen aus: {config_path}")
            return config
        except FileNotFoundError:
            print(f"Konfigurationsdatei nicht gefunden: {config_path}")
            print("Verwende Standard-Konfiguration...")
            return self.get_default_config()
        except Exception as e:
            print(f"Fehler beim Laden der Konfiguration: {e}")
            return self.get_default_config()
            
    def get_default_config(self) -> dict:
        """Standard-Konfiguration zurückgeben"""
        return {
            'network': {
                'discovery_port': 12345,
                'chat_port': 12346,
                'broadcast_address': '255.255.255.255',
                'discovery_interval': 30
            },
            'user': {
                'default_username': 'ChatUser',
                'max_message_length': 1024,
                'max_image_size': 1048576
            },
            'system': {
                'socket_timeout': 5,
                'worker_threads': 2,
                'log_level': 'INFO'
            }
        }
        
    def start(self):
        """Anwendung starten"""
        print(f"Starte Simple Chat für Nutzer: {self.username}")
        
        try:
            self.running = True
            
            # Chat Server starten
            self.chat_server.start()
            
            # Discovery Service starten
            self.discovery_service.start()
            
            # Cleanup-Thread starten
            cleanup_thread = threading.Thread(target=self.cleanup_loop)
            cleanup_thread.daemon = True
            cleanup_thread.start()
            
            # CLI starten (blockiert bis zum Ende)
            self.cli.start()
            
        except Exception as e:
            print(f"Fehler beim Starten: {e}")
        finally:
            self.shutdown()
            
    def cleanup_loop(self):
        """Regelmäßige Aufräumarbeiten"""
        while self.running:
            try:
                # Inaktive Nutzer entfernen (nach 60 Sekunden)
                self.ipc_handler.cleanup_inactive_users(60)
                time.sleep(30)  # Alle 30 Sekunden aufräumen
            except Exception as e:
                print(f"Cleanup Error: {e}")
                
    def shutdown(self):
        """Anwendung herunterfahren"""
        print("\nFahre Anwendung herunter...")
        self.running = False
        
        # Goodbye-Nachricht senden
        users = self.ipc_handler.get_active_users()
        if users:
            goodbye_msg = f"{self.username} hat den Chat verlassen."
            self.chat_client.broadcast_message(users, goodbye_msg, 'system')
            
        # Services stoppen
        self.cli.stop()
        self.chat_server.stop()
        self.discovery_service.stop()
        
        print("Anwendung beendet.")
        
    def signal_handler(self, signum, frame):
        """Signal-Handler für sauberes Beenden"""
        print("\nBeende Programm...")
        self.shutdown()
        sys.exit(0)

def parse_arguments():
    """Kommandozeilenargumente parsen"""
    parser = argparse.ArgumentParser(description='Simple Local Chat Protocol (SLCP)')
    parser.add_argument('-u', '--username', help='Nutzername für den Chat')
    parser.add_argument('-c', '--config', default='config.toml', 
                       help='Pfad zur Konfigurationsdatei (Standard: config.toml)')
    return parser.parse_args()

def main():
    """Hauptfunktion"""
    print("Simple Local Chat Protocol (SLCP)")
    print("Dezentrales Chat-System für lokale Netzwerke")
    print("=" * 50)
    
    # Argumente parsen
    args = parse_arguments()
    
    # Nutzername abfragen falls nicht angegeben
    username = args.username
    if not username:
        try:
            username = input("Nutzername eingeben: ").strip()
            if not username:
                username = "ChatUser"
        except (KeyboardInterrupt, EOFError):
            print("\nProgramm abgebrochen.")
            return
            
    # Chat-Anwendung erstellen und starten
    try:
        app = SimpleChatApp(args.config, username)
        app.start()
    except KeyboardInterrupt:
        print("\nProgramm durch Nutzer beendet.")
    except Exception as e:
        print(f"Unerwarteter Fehler: {e}")

if __name__ == "__main__":
    main()
