import socket
import threading
import time
import os
import subprocess
import platform
from typing import Dict, Any


class ChatServer:

    # Initialisiert den ChatServer mit der Konfiguration und dem IPC-Handler
    def __init__(self, config: Dict[str, Any], ipc_handler):
        self.config = config
        self.ipc_handler = ipc_handler
        self.running = False
        self.server_socket = None

    # Ermittelt einen freien TCP-Port, indem ein Socket gebunden wird
    def get_free_tcp_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    # Start Funktion des Servers
    def start(self):
        self.running = True # Setzt den Server in den laufenden Zustand
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Erstellt einen TCP-Socket
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.settimeout(1) # Timeout

        # Versucht, den Server auf dem konfigurierten Port zu starten
        # Wenn der Port bereits belegt ist, wird ein freier Port gesucht
        # und der Server auf diesem Port gestartet
        try:
            configured_port = self.config['network'].get('chat_port', 0)
            
            try:
                self.server_socket.bind(('', configured_port))
            
            #Error-Handling für den Fall, dass der Port bereits belegt ist
            except OSError:
                configured_port = self.get_free_tcp_port()
                self.server_socket.bind(('', configured_port))

            self.config['network']['chat_port'] = configured_port
            self.server_socket.listen(5)
            print(f"[Server] Lauscht auf TCP-Port {configured_port}") # Ausgabe für Benutzer
            threading.Thread(target=self.accept_connections, daemon=True).start() # Startet einen Thread, der auf eingehende Verbindungen wartet

        #Error-Handling
        except Exception as e:
            print(f"Fehler beim Serverstart: {e}")
            self.running = False

    # Stoppt den Server und schließt den Socket
    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()

    # Verbindungen akzeptieren
    def accept_connections(self):
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Verbindungsfehler: {e}")

    # Verarbeitet eingehende Nachrichten von Clients
    def handle_client(self, client_socket: socket.socket, addr):
        try:
            with client_socket.makefile("rb") as sockfile:
                line = sockfile.readline().decode("utf-8", errors="ignore").strip()
                parts = line.split(" ", 2)
                cmd = parts[0].upper()

                # Normale Text Nachrichten
                if cmd == "MSG" and len(parts) >= 3:
                    recipient = parts[1]
                    message = parts[2]
                    display_msg = {
                        'type': 'text',
                        'sender_ip': addr[0],
                        'content': message,
                        'timestamp': time.time()
                    }
                    self.ipc_handler.send_message(display_msg)

                # Image Nachrichten
                elif cmd == "IMG" and len(parts) == 3:
                    recipient = parts[1]
                    try:
                        size = int(parts[2])

                    #Error-Handling für ungültige Bildgrößen
                    except ValueError:
                        print(f"Ungültige Bildgröße: {parts[2]}")
                        return

                    image_data = sockfile.read(size)

                    folder = self.config.get("system", {}).get("imagepath", "images")
                    os.makedirs(folder, exist_ok=True)

                    ext = ".bin"
                    #Verschiedene Dateiendungen für verschiedene Bildformate
                    if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
                        ext = ".png"
                    elif image_data.startswith(b"\xff\xd8"):
                        ext = ".jpg"
                    elif image_data.startswith(b"GIF87a") or image_data.startswith(b"GIF89a"):
                        ext = ".gif"

                    # Generiere einen Dateinamen mit Zeitstempel
                    # und speichere das Bild im angegebenen Ordner
                    filename = f"received_{int(time.time())}{ext}"
                    filepath = os.path.join(folder, filename) #
                    with open(filepath, "wb") as f:
                        f.write(image_data) # Speichert die Bilddaten in der Datei

                    #Inhalt der Nachricht für die Anzeige
                    display_msg = {
                        'type': 'image',
                        'sender_ip': addr[0],
                        'filename': filepath,
                        'timestamp': time.time()
                    }
                    self.ipc_handler.send_message(display_msg) # sendet die Nachricht an den IPC-Handler

                    # Bild automatisch öffnen (optional)
                    if self.config.get("system", {}).get("image_autoview", True):
                        try:
                            if platform.system() == "Linux":
                                subprocess.Popen(["xdg-open", filepath])
                            elif platform.system() == "Darwin":
                                subprocess.Popen(["open", filepath])
                            elif platform.system() == "Windows":
                                os.startfile(filepath)
                        except Exception as e:
                            print(f"[Bildanzeige] Fehler beim Öffnen: {e}")

                # Leave System Nachrichten
                elif cmd == "LEAVE" and len(parts) == 2:
                    handle = parts[1]

                    # Entferne den Benutzer aus der Benutzerliste
                    self.ipc_handler.remove_user_by_name(handle)

                    #Inhalt der Nachricht für die Anzeige
                    display_msg = {
                        'type': 'system',
                        'content': f"{handle} hat den Chat verlassen.", # handle ist hier der Benutzer der den Chat verlässt
                        'timestamp': time.time()
                    }

                    #Nachricht an IPC-Handler senden
                    self.ipc_handler.send_message(display_msg)

                # Known Users System Nachrichten
                elif cmd == "KNOWUSERS":
                    entries = line[10:].split(",") # Teile die KNOWUSERS-Nachricht in ihre Bestandteile auf

                    for entry in entries:
                        entry_parts = entry.strip().split(" ")

                        # Prüfe, ob die Einträge die erwartete Struktur haben
                        if len(entry_parts) == 3:
                            handle, ip, port = entry_parts

                            if handle != self.config.get("handle"):
                                # Aktualisiere die Benutzerliste im IPC-Handler
                                # wenn alles in Ordnung ist
                                self.ipc_handler.update_user_list(handle, ip, int(port), time.time())

        #Error Handling
        except Exception as e:
            print(f"Fehler bei Nachricht: {e}")
        #
        # Schließe den Client-Socket, wenn die Verarbeitung abgeschlossen ist
        finally:
            client_socket.close()
