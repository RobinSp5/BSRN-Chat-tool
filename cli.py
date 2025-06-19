import threading
import time
import os
import shlex
import toml
from typing import Dict, Any
import socket


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

    #Zeigt die Willkommensnachricht an, wenn der Chat via CLI gestartet wird
    def show_welcome(self):
        print("=" * 50)
        print("     Simple Local Chat (SLCP)")
        print("=" * 50)
        print("📢 Du bist aktuell nicht im Chat angemeldet.")
        print("Melde dich mit /join <benutzername> an.")
        self.show_help()

    #Hilfsfunktion, um die Hilfe anzuzeigen
    # Hier die allgemeine Hilfe bearbeiten
    # Wird bei /help und bei initialem Start aufgerufen
    def show_help(self):
        print("Verfügbare Befehle:")
        print("  /join <name>         - Chat beitreten")
        print("  /who                 - Aktive Nutzer anzeigen")
        print("  /msg <text>          - Nachricht an alle senden")
        print("  /pm <user> <msg>     - Private Nachricht senden")
        print("  /img <user> <pfad>   - Bild privat senden")
        print("  /autoreply           - Autoreply-Modus aktivieren/deaktivieren")
        print("  /show_config         - Aktuelle Konfiguration anzeigen")
        print("  /edit_config <key> <value> - Konfiguration bearbeiten")
        print("  /quit                - Chat verlassen und beenden")

    #Haupt-Loop, die die Eingaben des Nutzers verarbeitet
    def command_loop(self):
        while self.running:
            try:
                user_input = input("> ").strip()
                self.last_input_time = time.time()
                if self.autoreply_active:
                    self.autoreply_active = False
                    self.ipc_handler.set_visibility(True)
                    print("🟢 Du bist wieder aktiv.")
                    self.discovery_service.request_discovery()
                if not user_input:
                    continue
                if not user_input.startswith("/"):
                    print("Befehle müssen mit '/' beginnen.")
                    continue
                self.process_command(user_input[1:])
            except (KeyboardInterrupt, EOFError):
                print("\nChat wird beendet.")
                self.running = False

    # Überwacht die Inaktivität des Nutzers und aktiviert den Autoreply-Modus
    # Wenn der Nutzer länger als inactivity_timeout Sekunden inaktiv ist,
    def inactivity_monitor(self):
        while self.running:
            if time.time() - self.last_input_time > self.inactivity_timeout and not self.autoreply_active:
                self.autoreply_active = True
                self.ipc_handler.set_visibility(False)
                print("\n🟡 Du bist inaktiv – Autoreply-Modus aktiviert.")
                print("> ", end="", flush=True)
                self.discovery_service.request_discovery() # Sendet eine WHO-Anfrage an den Discovery Dienst, um aktive Nutzer zu finden
            time.sleep(1)

    def process_command(self, command: str):
        try:
            parts = shlex.split(command)
            if not parts:
                return
            cmd = parts[0].lower()

            if cmd == "help":
                self.show_help() #Ruft die Hilfsfunktion auf, um die verfügbaren Befehle anzuzeigen

            elif cmd == "join":
                #Teilt den Befehl in Teile auf und prüft, ob genau 2 Argumente vorhanden sind
                if len(parts) < 2:
                    print("Verwendung: /join <benutzername>")
                    return
                
                name = parts[1].strip()
                #Prüft, ob das zweite Argument (Name) leer ist
                if not name:
                    print("Name darf nicht leer sein.")
                    return
                self.chat_client.username = name
                self.discovery_service.username = name
                self.discovery_service.send_join()
                print(f"Du hast dich erfolgreich als \"{name}\" im Chat angemeldet.")

            elif cmd == "who":
                self.discovery_service.request_discovery()
                time.sleep(2)
                self.show_active_users()

            elif cmd == "msg":
                if len(parts) >= 2:
                    self.discovery_service.request_discovery()
                    self.send_broadcast_message(" ".join(parts[1:]))
                else:
                    print("Verwendung: /msg <nachricht>")

            elif cmd == "pm":
                if len(parts) >= 3:
                    self.send_private_message(parts[1], " ".join(parts[2:]))
                else:
                    print("Verwendung: /pm <nutzer> <nachricht>")

            elif cmd == "img":
                if len(parts) >= 3:
                    self.send_image_to_user(parts[1], " ".join(parts[2:]))
                else:
                    print("Verwendung: /img <nutzer> <pfad>")

            elif cmd == "quit":
                if self.chat_client.username:
                    self.discovery_service.send_leave()
                self.running = False

            elif cmd == "show_config":
                print("Aktuelle Konfiguration:")
                for key, value in self.config.items():
                    print(f"  {key}: {value}")


            # Bearbeitet die toml Datei
            # Der Benutzer kann nur das Feld "handle" bearbeiten
            elif cmd == "edit_config":
                if len(parts) == 3:
                    key = parts[1].strip()
                    value = parts[2].strip()
                    
                    # Erlaubt nur das Bearbeiten des "handle"-Feldes
                    if key == "handle":
                        try:
                            # Update
                            self.config[key] = value
                            
                            # Updated den username im chat_client und discovery_service
                            old_username = self.chat_client.username
                            
                            # Updated das config.toml file
                            config_file = "config.toml"  # Adjust path if needed
                            
                            # Liest das aktuelle config file
                            with open(config_file, 'r', encoding='utf-8') as f:
                                config_data = toml.load(f)
                            
                            # Update nur den Wert im handle Feld
                            config_data['handle'] = value
                            
                            # Schreibt die aktualisierte Konfiguration zurück in die Datei
                            with open(config_file, 'w', encoding='utf-8') as f:
                                toml.dump(config_data, f)
                            
                            print(f"Konfiguration aktualisiert: {key} = {value}")
                            if old_username:
                                print(f"Username wird geändert von '{old_username}' zu '{value}'...")
                                # Sendet LEAVE, um den alten Namen zu verlassen
                                self.discovery_service.send_leave()
                                print(f"LEAVE gesendet für '{old_username}'")
                                time.sleep(1)  # Pause
                                
                                # Neue Username setzen
                                self.chat_client.username = value
                                self.discovery_service.username = value
                                
                                # Loescht die lokale User-Informationen
                                self.ipc_handler.remove_user_by_name(old_username)
                                
                                # Neu joinen mit neuen Username
                                self.discovery_service.send_join()
                                local_ip = self.chat_client.config['network'].get('local_ip', '127.0.0.1')
                                tcp_port = self.chat_client.config['network'].get('chat_port', 5001)

                                # Eigenen neuen Username zur Liste hinzufügen
                                # Wurde vorher nicht angezeigt wenn man selbst den Namen gaendert hat
                                # und dann /who gemacht hat
                                self.ipc_handler.update_user_list(value, local_ip, tcp_port, time.time())


                                print(f"JOIN gesendet für '{value}' - Username-Wechsel abgeschlossen!")
                                
                                # Discovery Service anfordern, um andere Nutzer zu benachrichtigen
                                time.sleep(0.5)
                                self.discovery_service.request_discovery()
                            else:
                                #
                                self.chat_client.username = value
                                self.discovery_service.username = value
                                print("Username gesetzt - sofort aktiv!")
                            
                        except FileNotFoundError: # FileNotFoundError wird geworfen, wenn die config.toml Datei nicht gefunden wird
                            print("Fehler: config.toml nicht gefunden.")
                        except Exception as e: # Allgemeiner Fehler beim Speichern der Konfiguration
                            print(f"Fehler beim Speichern der Konfiguration: {e}")
                    else:# Nur das Feld "handle" kann bearbeitet werden
                        print("Nur das Feld 'handle' kann bearbeitet werden.")
                        print("Verwendung: /edit_config handle <neuer_username>")
                else: # Wenn die Anzahl der Argumente nicht 3 ist, wird eine Fehlermeldung ausgegeben
                    print("Verwendung: /edit_config handle <neuer_username>")

            elif cmd == "autoreply":
                if self.autoreply_active:
                    self.autoreply_active = False
                    self.ipc_handler.set_visibility(True)
                    print("🟢 Autoreply-Modus deaktiviert.")
                else:
                    self.autoreply_active = True
                    self.ipc_handler.set_visibility(False)
                    print("🟡 Autoreply-Modus aktiviert. Du bist jetzt inaktiv.")
                    self.discovery_service.request_discovery()


            else:
                print(f"Unbekannter Befehl: {cmd}")

        except Exception as e:
            print(f"Fehler beim Verarbeiten des Befehls: {e}")

    def show_help(self):
        print("Verfügbare Befehle:")
        print("  /join <name>         - JOIN senden (Chat beitreten)")
        print("  /who                 - WHO senden (aktive Nutzer abfragen)")
        print("  /msg <text>          - Nachricht an alle")
        print("  /pm <user> <msg>     - Private Nachricht")
        print("  /img <user> <pfad>   - Bild privat senden")
        print("  /show_config         - Aktuelle Konfiguration anzeigen")
        print("  /edit_config <key> <value> - Konfiguration bearbeiten")
        print("  /quit                - LEAVE senden & beenden")

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
            print("Bitte zuerst mit /join <name> beitreten.")
            return
        users = self.ipc_handler.get_active_users()
        if not users:
            print("Keine Nutzer zum Senden.")
            return
        sent = 0
        for name, info in users.items():
            if name != self.chat_client.username:
                if self.chat_client.send_text_message(info['ip'], info['tcp_port'], name, message):
                    sent += 1
        print(f"Nachricht gesendet an {sent} / {len(users) - 1 if self.chat_client.username in users else len(users)}")

    def send_private_message(self, username: str, message: str):
        if not self.chat_client.username:
            print("Bitte zuerst mit /join <name> beitreten.")
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
            print(f"Senden fehlgeschlagen an {username}.")

    def send_image_to_user(self, username: str, image_path: str):
        if not self.chat_client.username:
            print("Bitte zuerst mit /join <name> beitreten.")
            return
        if not os.path.isfile(image_path):
            print(f"Bild nicht gefunden: {image_path}")
            return
        users = self.ipc_handler.get_active_users()
        user = users.get(username)
        if not user:
            print(f"Nutzer {username} nicht bekannt.")
            return
        success = self.chat_client.send_image_message(user['ip'], user['tcp_port'], username, image_path)
        if success:
            print(f"[Bild → {username}]: {os.path.basename(image_path)} gesendet.")
        else:
            print(f"Senden des Bildes an {username} fehlgeschlagen.")

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
            sender_name = None
            users = self.ipc_handler.get_active_users(only_visible=False)
            for name, info in users.items():
                if info["ip"] == sender_ip:
                    sender_name = name
                    break
            local_ip = self.chat_client.config['network'].get('local_ip', '')
            if sender_ip == local_ip and sender_name is None:
                sender_name = self.chat_client.username
            display_name = sender_name if sender_name else sender_ip
            print(f"\n[{time_str}] Nachricht von {display_name}: {message.get('content')}")

            if self.autoreply_active and sender_name:
                reply = self.config["system"].get("autoreply", "Ich bin gerade nicht verfügbar.")
                self.chat_client.send_text_message(sender_ip, info["tcp_port"], sender_name, reply)

        elif msg_type == 'image':
            print(f"\n[{time_str}] Bild empfangen von {sender_ip}: {message.get('filename')}")
        elif msg_type == 'system':
            print(f"\n[{time_str}] SYSTEM: {message.get('content')}")
        print("> ", end="", flush=True)


