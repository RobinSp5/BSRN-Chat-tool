import threading
import time
import os
import shlex
import toml
from typing import Dict, Any


class CLI:
    def __init__(self, config: Dict[str, Any], ipc_handler, chat_client, discovery_service):
        self.config = config
        self.ipc_handler = ipc_handler
        self.chat_client = chat_client
        self.discovery_service = discovery_service
        self.running = False
        self.last_input_time = time.time()
        self.inactivity_timeout = 60
        self.autoreply_active = False

    def start(self):
        self.running = True
        threading.Thread(target=self.display_messages, daemon=True).start()
        threading.Thread(target=self.inactivity_monitor, daemon=True).start()
        self.show_welcome()
        self.command_loop()

    def stop(self):
        self.running = False

    def show_welcome(self):
                print("=" * 50)
                print("     Simple Local Chat (SLCP)")
                print("=" * 50)
                print("📢 Du bist aktuell nicht im Chat angemeldet.")
                print("Melde dich mit /join <benutzername> an.")
                print("Verfügbare Befehle (alle mit '/'): ")
                print("  /help           - Hilfe anzeigen")
                print("  /join <name>    - Chat beitreten (JOIN)")
                print("  /who            - Nutzer suchen (WHO)")
                print("  /msg <text>     - Nachricht an alle senden")
                print("  /pm <user> <msg>- Private Nachricht senden")
                print("  /img <pfad>     - Bild an alle senden")
                print("  /show_config    - Aktuelle Konfiguration anzeigen")
                print("  /edit_config <key> <value> - Konfiguration bearbeiten")
                print("  /quit           - Chat verlassen")
                print("-" * 50)

    def command_loop(self):
        while self.running:
            try:
                user_input = input("> ").strip()
                self.last_input_time = time.time()
                if self.autoreply_active:
                    self.autoreply_active = False
                    self.ipc_handler.set_visibility(True)
                    print("🟢 Du bist wieder aktiv.")
                if not user_input:
                    continue
                if not user_input.startswith("/"):
                    print("⚠️  Befehle müssen mit '/' beginnen.")
                    continue
                self.process_command(user_input[1:])
            except (KeyboardInterrupt, EOFError):
                print("\nChat wird beendet.")
                self.running = False

    def inactivity_monitor(self):
        while self.running:
            if time.time() - self.last_input_time > self.inactivity_timeout and not self.autoreply_active:
                self.autoreply_active = True
                self.ipc_handler.set_visibility(False)
                print("\n🟡 Du bist inaktiv – Autoreply-Modus aktiviert.")
                print("> ", end="", flush=True)
            time.sleep(1)

    def process_command(self, command: str):
        try:
            parts = shlex.split(command)
            if not parts:
                return
            cmd = parts[0].lower()

            if cmd == "help":
                self.show_help()

            elif cmd == "join":
                if len(parts) < 2:
                    print("Verwendung: /join <benutzername>")
                    return
                name = parts[1].strip()
                if not name:
                    print("⚠️ Name darf nicht leer sein.")
                    return
                self.chat_client.username = name
                self.discovery_service.username = name
                self.discovery_service.send_join()
                print(f"✅ Du hast dich erfolgreich als \"{name}\" im Chat angemeldet.")

            elif cmd == "who":
                self.discovery_service.request_discovery()
                time.sleep(2)
                self.show_active_users()

            elif cmd == "msg":
                if len(parts) >= 2:
                    self.send_broadcast_message(" ".join(parts[1:]))
                else:
                    print("Verwendung: /msg <nachricht>")

            elif cmd == "pm":
                if len(parts) >= 3:
                    self.send_private_message(parts[1], " ".join(parts[2:]))
                else:
                    print("Verwendung: /pm <nutzer> <nachricht>")

            elif cmd == "img":
                if len(parts) >= 2:
                    self.send_image_broadcast(" ".join(parts[1:]))
                else:
                    print("Verwendung: /img <pfad>")
            elif cmd == "quit":
                if self.chat_client.username:
                    self.discovery_service.send_leave()
                    print(f"🚪 {self.chat_client.username} hat den Chat verlassen.")
                self.running = False

            elif cmd == "show_config":
                print("Aktuelle Konfiguration:")
                for key, value in self.config.items():
                    print(f"  {key}: {value}")
                        elif cmd == "edit_config":
                        # Prüfen ob mindestens Schlüssel und Wert angegeben wurden
                        if len(parts) >= 3:
                            key = parts[1]
                            # Hier alle weiteren Teile als einen zusammenhängenden Wert nehmen
                            value = " ".join(parts[2:])
                            # Verschachtelte Konfigurationsschlüssel wie "system.autoreply" behandeln
                            if "." in key:
                                config_section, config_key = key.split(".", 1)
                                if config_section in self.config:
                                    if not isinstance(self.config[config_section], dict):
                                        self.config[config_section] = {}
                                    self.config[config_section][config_key] = value
                                    print(f"✅ Konfiguration aktualisiert: {key} = {value}")
                                else:
                                    print(f"⚠️ Konfigurationssektion '{config_section}' nicht gefunden.")
                            else:
                                # Einfache Schlüssel wie "name" behandeln
                                self.config[key] = value
                                print(f"✅ Konfiguration aktualisiert: {key} = {value}")

                            # In die TOML-Datei speichern
                            try:
                                config_path = "config.toml"  # ggf. aus self.config holen
                                with open(config_path, "w") as f:
                                    toml.dump(self.config, f)
                                print(f"💾 Konfiguration in {config_path} gespeichert.")
                            except Exception as e:
                                print(f"⚠️ Fehler beim Speichern der Konfiguration: {e}")
                        else:
                            # Usage-Hinweis
                            print("Verwendung: /edit_config <schlüssel> <wert>")
                            print("Beispiele:")
                            print("  /edit_config name Alice")
                            print("  /edit_config system.autoreply \"Bin gleich zurück\"")


            else:
                print(f"Unbekannter Befehl: {cmd}")

        except Exception as e:
            print(f"⚠️ Fehler beim Verarbeiten des Befehls: {e}")

    def show_help(self):
        print("Verfügbare Befehle:")
        print("  /join <name>    - JOIN senden (Chat beitreten)")
        print("  /who            - WHO senden (aktive Nutzer abfragen)")
        print("  /msg <text>     - Nachricht an alle")
        print("  /pm <user> <msg>- Private Nachricht")
        print("  /img <pfad>     - Bild an alle")
        print("  /quit           - LEAVE senden & beenden")

    def show_active_users(self):
        users = self.ipc_handler.get_active_users()
        if not users:
            print("Keine Nutzer bekannt.")
            return
        print("Aktive Nutzer:")
        for name, info in users.items():
            print(f"  {name} @ {info['ip']}:{info['tcp_port']}")

    def send_broadcast_message(self, message: str):
        if not self.chat_client.username:
            print("⚠️ Bitte zuerst mit /join <name> beitreten.")
            return
        users = self.ipc_handler.get_active_users()
        if not users:
            print("❌ Keine Nutzer zum Senden.")
            return
        sent = 0
        for name, info in users.items():
            if self.chat_client.send_text_message(info['ip'], info['tcp_port'], name, message):
                sent += 1
        print(f"Nachricht gesendet an {sent}/{len(users)}")

    def send_private_message(self, username: str, message: str):
        if not self.chat_client.username:
            print("⚠️ Bitte zuerst mit /join <name> beitreten.")
            return
        users = self.ipc_handler.get_active_users()
        user = users.get(username)
        if not user:
            print(f"Nutzer {username} nicht bekannt.")
            return
        success = self.chat_client.send_text_message(user['ip'], user['tcp_port'], username, message)
        if success:
            print(f"[Du → {username}]: {message}")
        else:
            print(f"❌ Senden fehlgeschlagen an {username}.")

    def send_image_broadcast(self, image_path: str):
        if not self.chat_client.username:
            print("⚠️ Bitte zuerst mit /join <name> beitreten.")
            return
        if not os.path.isfile(image_path):
            print(f"❌ Bild nicht gefunden: {image_path}")
            return
        users = self.ipc_handler.get_active_users()
        if not users:
            print("❌ Keine Nutzer bekannt.")
            return
        sent = 0
        for name, info in users.items():
            if self.chat_client.send_image_message(info['ip'], info['tcp_port'], name, image_path):
                sent += 1
        print(f"Bild gesendet an {sent}/{len(users)}")

    def display_messages(self):
        while self.running:
            message = self.ipc_handler.get_message()
            if message:
                self.show_message(message)
            time.sleep(0.1)

    def show_message(self, message: Dict[str, Any]):
        msg_type = message.get('type')
        sender_ip = message.get('sender_ip', 'Unbekannt')
        timestamp = message.get('timestamp', 0)
        time_str = time.strftime('%H:%M:%S', time.localtime(timestamp))

        if msg_type == 'text':
            print(f"\n[{time_str}] Nachricht von {sender_ip}: {message.get('content')}")
            if self.autoreply_active:
                sender_name = None
                users = self.ipc_handler.get_active_users(only_visible=False)
                for name, info in users.items():
                    if info["ip"] == sender_ip:
                        sender_name = name
                        break
                if sender_name:
                    reply = self.config["system"].get("autoreply", "Ich bin gerade nicht verfügbar.")
                    self.chat_client.send_text_message(sender_ip, info["tcp_port"], sender_name, reply)

        elif msg_type == 'image':
            print(f"\n[{time_str}] Bild empfangen von {sender_ip}: {message.get('filename')}")
        elif msg_type == 'system':
            print(f"\n[{time_str}] SYSTEM: {message.get('content')}")
        print("> ", end="", flush=True)