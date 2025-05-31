"""
Command Line Interface für das Chat-Programm
Verarbeitet Nutzerbefehle und zeigt Nachrichten an
"""

import threading
import time
import os
from typing import Dict, Any

class CLI:
    def __init__(self, config: Dict[str, Any], ipc_handler, chat_client, discovery_service):
        self.config = config
        self.ipc_handler = ipc_handler
        self.chat_client = chat_client
        self.discovery_service = discovery_service
        self.running = False
        
    def start(self):
        """CLI starten"""
        self.running = True
        
        # Message Display Thread
        display_thread = threading.Thread(target=self.display_messages)
        display_thread.daemon = True
        display_thread.start()
        
        # Command Input Loop
        self.show_welcome()
        self.command_loop()
        
    def stop(self):
        """CLI stoppen"""
        self.running = False
        
    def show_welcome(self):
        """Willkommensnachricht anzeigen"""
        print("=" * 50)
        print("     Simple Local Chat (SLCP)")
        print("=" * 50)
        print(f"Nutzer: {self.chat_client.username}")
        print("Verfügbare Befehle (alle mit '/'): ")
        print("  /help           - Hilfe anzeigen")
        print("  /who            - Aktive Nutzer anzeigen")
        print("  /msg <text>     - Nachricht an alle senden")
        print("  /pm <user> <msg>- Private Nachricht senden")
        print("  /img <path>     - Bild an alle senden")
        print("  /refresh        - Nutzer neu suchen")
        print("  /quit           - Programm beenden")
        print("-" * 50)
        
    def command_loop(self):
        """Haupt-Befehlsschleife"""
        while self.running:
            try:
                # Eingabe abholen
                user_input = input("> ").strip()
                if not user_input:
                    continue

                # Eingabe muss mit '/' beginnen
                if not user_input.startswith("/"):
                    print("⚠️  Ungültiger Befehl. Befehle müssen mit '/' beginnen (z.B. /msg Hallo)")
                    continue

                # Slash entfernen und verarbeiten
                command = user_input[1:]
                self.process_command(command)
                
            except KeyboardInterrupt:
                print("\nProgramm wird beendet...")
                break
            except EOFError:
                break
                
    def process_command(self, command: str):
        """Einzelnen Befehl verarbeiten"""
        parts = command.split(' ', 2)
        cmd = parts[0].lower()
        
        if cmd == 'help':
            self.show_help()
        elif cmd == 'who':
            self.show_active_users()
        elif cmd == 'msg':
            if len(parts) >= 2:
                message = ' '.join(parts[1:])
                self.send_broadcast_message(message)
            else:
                print("Verwendung: /msg <nachricht>")
        elif cmd == 'pm':
            if len(parts) >= 3:
                username = parts[1]
                message = ' '.join(parts[2:])
                self.send_private_message(username, message)
            else:
                print("Verwendung: /pm <nutzer> <nachricht>")
        elif cmd == 'img':
            if len(parts) >= 2:
                image_path = parts[1]
                self.send_image_broadcast(image_path)
            else:
                print("Verwendung: /img <pfad>")
        elif cmd == 'refresh':
            self.refresh_users()
        elif cmd == 'quit' or cmd == 'exit':
            self.running = False
        else:
            print(f"Unbekannter Befehl: {cmd}. /help für Hilfe.")
    
    def show_help(self):
        """Hilfenachricht anzeigen"""
        print("Verfügbare Befehle:")
        print("  /help           - Diese Hilfe anzeigen")
        print("  /who            - Aktive Nutzer anzeigen")
        print("  /msg <text>     - Nachricht an alle senden")
        print("  /pm <user> <msg>- Private Nachricht senden")
        print("  /img <path>     - Bild an alle senden")
        print("  /refresh        - Nutzer neu suchen")
        print("  /quit           - Programm beenden")
    
    def show_active_users(self):
        """Aktive Nutzer anzeigen"""
        users = self.ipc_handler.get_active_users()
        if not users:
            print("Keine aktiven Nutzer gefunden.")
            return
            
        print(f"Aktive Nutzer ({len(users)}):")
        for username, user_info in users.items():
            ip = user_info.get('ip', 'Unbekannt')
            last_seen = user_info.get('last_seen', 0)
            if last_seen:
                time_str = time.strftime('%H:%M:%S', time.localtime(last_seen))
                print(f"  {username} ({ip}) - zuletzt gesehen: {time_str}")
            else:
                print(f"  {username} ({ip})")
    
    def send_broadcast_message(self, message: str):
        """Nachricht an alle Nutzer senden"""
        users = self.ipc_handler.get_active_users()
        if not users:
            print("Keine aktiven Nutzer zum Senden.")
            return
            
        successful_sends = 0
        for username, user_info in users.items():
            target_ip = user_info.get('ip')
            if target_ip and self.chat_client.send_text_message(target_ip, message):
                successful_sends += 1
                
        print(f"Nachricht an {successful_sends} von {len(users)} Nutzern gesendet.")
    
    def send_private_message(self, username: str, message: str):
        """Private Nachricht an bestimmten Nutzer senden"""
        users = self.ipc_handler.get_active_users()
        if username not in users:
            print(f"Nutzer '{username}' nicht gefunden.")
            return
            
        user_info = users[username]
        target_ip = user_info.get('ip')
        
        if target_ip and self.chat_client.send_text_message(target_ip, message):
            print(f"Private Nachricht an {username} gesendet.")
        else:
            print(f"Fehler beim Senden der Nachricht an {username}.")
        
    def send_image_broadcast(self, image_path: str):
        """Bild an alle Nutzer senden"""
        if not os.path.exists(image_path):
            print(f"Datei nicht gefunden: {image_path}")
            return
            
        users = self.ipc_handler.get_active_users()
        if not users:
            print("Keine aktiven Nutzer zum Senden.")
            return
            
        successful_sends = 0
        for username, user_info in users.items():
            target_ip = user_info.get('ip')
            if target_ip and self.chat_client.send_image_message(target_ip, image_path):
                successful_sends += 1
                
        print(f"Bild an {successful_sends} von {len(users)} Nutzern gesendet.")
        
    def refresh_users(self):
        """Aktive Nutzer neu suchen"""
        print("Suche nach aktiven Nutzern...")
        self.discovery_service.request_discovery()
        time.sleep(2)  # Kurz warten für Antworten
        self.show_active_users()
        
    def display_messages(self):
        """Eingehende Nachrichten anzeigen"""
        while self.running:
            message = self.ipc_handler.get_message()
            if message:
                self.show_message(message)
            time.sleep(0.1)
            
    def show_message(self, message: Dict[str, Any]):
        """Einzelne Nachricht anzeigen"""
        msg_type = message.get('type', 'unknown')
        sender = message.get('sender', 'Unknown')
        timestamp = message.get('timestamp', 0)
        
        # Zeitstempel formatieren
        time_str = time.strftime('%H:%M:%S', time.localtime(timestamp))
        
        if msg_type == 'text':
            content = message.get('content', '')
            print(f"\n[{time_str}] {sender}: {content}")
        elif msg_type == 'image':
            filename = message.get('filename', 'image')
            print(f"\n[{time_str}] {sender} hat ein Bild gesendet: {filename}")
            image_data = message.get('image_data', '')
            if image_data:
                self.save_received_image(image_data, filename, sender)
        elif msg_type == 'system':
            content = message.get('content', '')
            print(f"\n[{time_str}] System: {content}")
            
        print("> ", end="", flush=True)
        
    def save_received_image(self, image_data: str, filename: str, sender: str):
        """Empfangenes Bild speichern"""
        try:
            import base64
            image_bytes = base64.b64decode(image_data)
            safe_filename = f"{sender}_{filename}"
            with open(safe_filename, 'wb') as f:
                f.write(image_bytes)
            print(f"Bild gespeichert als: {safe_filename}")
        except Exception as e:
            print(f"Fehler beim Speichern des Bildes: {e}")
