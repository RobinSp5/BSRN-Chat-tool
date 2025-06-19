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
                if len(parts) < 2:
                    print("Fehler: Du musst einen Benutzernamen angeben. Beispiel: /join Alice")
                    return  # KORREKTUR: return statt continue

                new_username = parts[1].strip()
                if not new_username:
                    print("Fehler: Der Benutzername darf nicht leer sein.")
                    return  # KORREKTUR: return statt continue

                #print(f"--- [JOIN Prozess für '{new_username}'] ---")

                # Schritt 1: Konfiguration im Speicher aktualisieren
                self.config['handle'] = new_username
                #print(f"1. Speicher aktualisiert: handle = '{self.config.get('handle')}'")

                # Schritt 2: Konfiguration in die Datei config.toml schreiben
                config_path = "config.toml"
                try:
                    #print(f"2. Versuche, in '{config_path}' zu schreiben...")
                    with open(config_path, "w") as f:
                        toml.dump(self.config, f)
                    print(f"   Erfolgreich in Datei gespeichert.")
                except Exception as e:
                    print(f"   ‼FEHLER BEIM SPEICHERN DER DATEI: {e}")
                    print("   Der Beitritt wird abgebrochen. Bitte prüfe die Dateiberechtigungen.")
                    return  # KORREKTUR: return statt continue

                # Schritt 3: Interne Services mit neuem Namen aktualisieren
                self.chat_client.username = new_username
                self.discovery_service.username = new_username
                #print("3. Interne Services aktualisiert.")

                # Schritt 4: JOIN-Nachricht senden
                if not self.discovery_service.running:
                    self.discovery_service.start()
                
                self.discovery_service.send_join()
                print("JOIN-Nachricht gesendet.")
                #print(f"--- [JOIN Prozess für '{new_username}' abgeschlossen] ---")
                print(f"Du bist jetzt als '{new_username}' im Chat aktiv.")

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
                            # Verwende die neue change_handle Funktion aus dem DiscoveryService
                            success = self.discovery_service.change_handle(value)
                            if success:
                                # Username auch im chat_client aktualisieren
                                self.chat_client.username = value
                                self.config['handle'] = value
                                print(f"Handle erfolgreich geändert zu: {value}")
                            else:
                                print("Fehler beim Ändern des Handles.")
                        else:
                            print("Nur das Feld 'handle' kann bearbeitet werden.")
                            print("Verwendung: /edit_config handle <neuer_username>")
                    else:
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

        # Den eigenen Nutzer manuell eintragen
        own_name = self.chat_client.username
        if own_name and own_name not in users:
            users[own_name] = {
            "ip": self.chat_client.config["network"].get("local_ip", "127.0.0.1"),
            "tcp_port": self.chat_client.config["network"].get("chat_port", 5001),
            "status": "online",
            "last_seen": time.time(),
            "visible": True
        }

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

    def handle_command(self, user_input: str):
        """
        Diese Methode verarbeitet ALLE Benutzereingaben.
        Sie ist so aufgebaut, dass Zustandsfehler vermieden werden.
        """
        parts = user_input.split(" ", 1)
        cmd = parts[0].lower()

        if cmd == "/join":
            if len(parts) < 2 or not parts[1].strip():
                print("\nFEHLER: Du musst einen Namen angeben. Beispiel: /join Peter\n")
                return

            new_username = parts[1].strip()
            print(f"\n--- [START] Ändere Namen zu '{new_username}' ---")

            # SCHRITT 1: Lade die Konfiguration IMMER frisch von der Festplatte.
            # Das verhindert, dass wir mit alten Daten arbeiten.
            config_path = "config.toml"
            try:
                with open(config_path, "r") as f:
                    current_config = toml.load(f)
                print("1. Aktuelle config.toml erfolgreich geladen.")
            except Exception as e:
                print(f"‼FEHLER: Konnte '{config_path}' nicht lesen: {e}")
                return

            # SCHRITT 2: Ändere den Namen im frisch geladenen Wörterbuch.
            current_config['handle'] = new_username
            print(f"2. Name im Speicher geändert auf '{current_config.get('handle')}'.")

            # SCHRITT 3: Schreibe das geänderte Wörterbuch zurück in die Datei.
            try:
                with open(config_path, "w") as f:
                    toml.dump(current_config, f)
                print(f"3. Änderungen wurden in '{config_path}' zurückgeschrieben.")
            except Exception as e:
                print(f"‼FEHLER: Konnte '{config_path}' nicht schreiben: {e}")
                return

            # SCHRITT 4: Aktualisiere die Konfiguration und den Namen in ALLEN laufenden Teilen des Programms.
            # Dies ist der entscheidende Schritt, um alle Teile zu synchronisieren.
            self.config = current_config
            self.chat_client.username = new_username
            self.discovery_service.username = new_username
            print("4. Laufende Programmteile wurden mit dem neuen Namen aktualisiert.")

            # SCHRITT 5: Sende die JOIN-Nachricht.
            if not self.discovery_service.running:
                self.discovery_service.start()
            self.discovery_service.send_join()
            print(f"5. JOIN als '{new_username}' gesendet.")
            print(f"--- [ENDE] Du bist jetzt als '{new_username}' im Chat aktiv. ---\n")

        elif cmd == "/show_config":
            print("\n--- Aktuelle Konfiguration (aus dem Speicher der CLI) ---")
            print(self.config)
            print("--------------------------------------------------------\n")

        elif cmd == "/quit":
            print("Beende das Programm...")
            if self.discovery_service.running:
                self.discovery_service.send_leave()
                self.discovery_service.stop()
            self.running = False # Beendet die Hauptschleife
        
        # Hier können weitere Befehle (elif cmd == "/who": ...) hinzugefügt werden.
        else:
            # Behandelt normale Chat-Nachrichten oder unbekannte Befehle
            if user_input.startswith('/'):
                print(f"Unbekannter Befehl: {cmd}")
            else:
                # Logik für das Senden von Broadcast-Nachrichten (/msg)
                print("Broadcast-Funktion hier einfügen.")


    def run(self):
        """
        Dies ist die Hauptschleife der CLI.
        Sie ruft für jede Eingabe die neue handle_command Methode auf.
        """
        self.running = True
        # Hier werden vermutlich deine Threads gestartet...
        # self.start_message_display_thread()

        while self.running:
            try:
                user_input = input("> ").strip()
                if user_input:
                    self.handle_command(user_input)
            except KeyboardInterrupt:
                self.handle_command("/quit")
        print("Programm beendet.")


