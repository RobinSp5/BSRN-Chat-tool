import socket
import threading
import time
from typing import Dict, Any
import toml


class DiscoveryService:
    def __init__(self, config: Dict[str, Any], ipc_handler, username: str, chat_tcp_port: int):
        
        #Kommentare für Debugging Ausgabe
        print(f"[Discovery] Initialisiere DiscoveryService mit:")
        print(f"            • Chat-Port (TCP): {chat_tcp_port}")
        print(f"            • Broadcast-Adresse: {config['network'].get('broadcast_address', '255.255.255.255')}")
        print(f"            • Discovery-Port (UDP): {config['network'].get('whoisport', 4000)}")

        # Initialisiert den Discovery-Service mit der Konfiguration, IPC-Handler, Benutzernamen und Chat-Port
        self.config = config
        self.ipc_handler = ipc_handler
        self.username = username
        self.chat_tcp_port = chat_tcp_port
        self.running = False

        # Setzt die Broadcast-IP und den Discovery-Port aus der Konfiguration
        self.broadcast_ip = self.config["network"].get("broadcast_address", "255.255.255.255")
        self.discovery_port = self.config["network"].get("whoisport", 4000)

        # Initialisiert den Discovery-Socket
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass
        self.listen_socket.settimeout(1)

    # Start Methode
    def start(self):
        # Ausgabe fuer den Nutzer...
        print("[Discovery] Starte Discovery-Service...")
        self.running = True

        # Versuche, den Discovery-Socket zu binden
        try:
            self.listen_socket.bind(('', self.discovery_port))
            threading.Thread(target=self.listen_loop, daemon=True).start()
        except OSError:
            # Falls das nicht klappt, gibt es einen Fehler
            print(f"[Discovery] Fehler: Port {self.discovery_port} bereits belegt oder nicht verfügbar.")

        # Sende eine JOIN-Nachricht an alle Peers im Netzwerk
        self.send_join()

    # Stop Methode
    def stop(self):
        # Ausgabe für den Nutzer...
        print("[Discovery] Beende Discovery-Service und schließe Socket...")
        self.running = False
        #self.send_leave()
        
        try:
            self.listen_socket.close() # Schließt den Discovery-Socket
        except Exception:
            pass

    # Haupt-Loop, der auf eingehende UDP-Nachrichten wartet
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

    # Diese Methode wird aufgerufen, wenn eine Nachricht empfangen wird
    # Sie analysiert die Nachricht und führt entsprechende Aktionen aus
    # wie JOIN, LEAVE, WHO und KNOWUSERS und verarbeitet die empfangenen Nachrichten
    # - aktualisiert die Benutzerliste entsprechend.
    # - sendet  Systemnachrichten an andere Peers, wenn nötig.
    def handle_message(self, message: str, sender_ip: str):

        # Join Nachrichten verarbeiten
        if message.startswith("JOIN"):
            parts = message.split(" ")

            # Teile die Nachricht in ihre Bestandteile auf
            if len(parts) == 3:
                peer, port = parts[1], int(parts[2])

                # Wenn der Peer nicht der eigene Benutzername ist, aktualisiere die Benutzerliste
                if peer != self.username:
                    known_users = self.ipc_handler.get_active_users(only_visible=False)
                    already_known = any(
                        u == peer and info["ip"] == sender_ip and info["tcp_port"] == port
                        for u, info in known_users.items()
                    )
                    # Aktualisiere die Benutzerliste mit dem neuen Peer
                    self.ipc_handler.update_user_list(peer, sender_ip, port, time.time())
                    if not already_known:
                        self.ipc_handler.send_message({
                            'type': 'system',
                            'content': f"JOIN {peer} {port}",
                            'timestamp': time.time()
                        })

        # Leave Nachrichten verarbeiten
        elif message.startswith("LEAVE"):
            parts = message.split(" ")
            if len(parts) == 2:
                peer = parts[1]
                if peer != self.username:
                    self.ipc_handler.remove_user_by_name(peer)
                    self.ipc_handler.send_message({
                        'type': 'system',
                        'content': f"LEAVE {peer}",
                        'timestamp': time.time()
                    })
        # WHO-Nachrichten verarbeiten
        elif message == "WHO":
            self.send_knowusers(sender_ip)

        # KNOWUSERS-Nachrichten verarbeiten
        elif message.startswith("KNOWUSERS"):
            payload = message[10:]
            
            # Teile die KNOWUSERS-Nachricht in ihre Bestandteile auf
            for chunk in payload.split(","):
                parts = chunk.strip().split(" ")
                if len(parts) == 3:
                    peer, ip, port = parts[0], parts[1], int(parts[2])
                    if peer != self.username:
                        self.ipc_handler.update_user_list(peer, ip, port, time.time()) # Aktualisiere die Benutzerliste

    # Sendet eine UDP-Broadcast-Nachricht an alle Peers im Netzwerk
    def send_udp_broadcast(self, text: str):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto((text + "\n").encode('utf-8'), (self.broadcast_ip, self.discovery_port))

    # Sendet eine JOIN-Nachricht an alle Peers im Netzwerk
    def send_join(self):
        if not self.username:
            return
        self.send_udp_broadcast(f"JOIN {self.username} {self.chat_tcp_port}")
        self.send_to_all_known_peers_as_knowuser()

    # Sendet eine LEAVE-Nachricht an alle Peers im Netzwerk
    def send_leave(self):
        self.send_udp_broadcast(f"LEAVE {self.username}")

    # Fordert eine Discovery-Nachricht an, um andere Peers zu finden
    def request_discovery(self):
        self.send_join()
        time.sleep(0.05)
        self.send_udp_broadcast("WHO")

    # Sendet eine KNOWUSERS-Nachricht an einen bestimmten Peer
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

        # Error-Handling
        except Exception as e:
            print(f"[Discovery] Fehler beim Senden von KNOWUSERS an {target_ip}:{target_port}: {e}")

    # Sendet die KNOWUSERS-Nachricht an alle bekannten Peers, nachdem der Peer dem Chat beigetreten ist
    def send_to_all_known_peers_as_knowuser(self):

        #Wird nach JOIN verwendet, um aktiv an andere Peers KNOWUSERS zu schicken
        users = self.ipc_handler.get_active_users(only_visible=True)
        if not users:
            return

        # Erstelle die KNOWUSERS-Nachricht mit der eigenen IP und dem Chat-Port
        # und sende sie an alle anderen Peers
        self_entry = f"{self.username} {self.config['network'].get('local_ip')} {self.chat_tcp_port}"
        msg = "KNOWUSERS " + self_entry + "\n"

        for name, info in users.items():
            if name == self.username:
                continue
            try:
                with socket.create_connection(
                    (info['ip'], info['tcp_port']),
                    timeout=self.config['system']['socket_timeout']
                ) as sock:
                    sock.sendall(msg.encode("utf-8"))

            # Error-Handling
            except Exception as e:
                print(f"[Discovery] Fehler bei aktivem Senden an {name}: {e}")


    # Extra Methode um den Handle bzw Benutzernamen zu ändern
    # Diese Methode aktualisiert den Benutzernamen und führt alle notwendigen Discovery-Operationen
    # durch, wie das Senden von LEAVE und JOIN-Nachrichten.
    # - aktualisiert den handle in der config.toml 
    # - alle Peers werden benachrichtigt
    # - gibt True zurück, wenn die Änderung erfolgreich war --> sonst False
    def change_handle(self, new_username: str, config_file_path: str = "config.toml"):

            if not new_username or not new_username.strip():
                print("[Discovery] Fehler: Neuer Username darf nicht leer sein.")
                return False
            
            old_username = self.username # Aktueller Username vor der Änderung
            new_username = new_username.strip() 

            try:
                # 1. Config-Datei aktualisieren
                try:
                    with open(config_file_path, 'r', encoding='utf-8') as f:
                        config_data = toml.load(f)
                    
                    config_data['handle'] = new_username
                    
                    with open(config_file_path, 'w', encoding='utf-8') as f:
                        toml.dump(config_data, f)
                        
                    print(f"[Discovery] config.toml aktualisiert: handle = {new_username}")
                except Exception as e:
                    print(f"[Discovery] Fehler beim Speichern der config.toml: {e}")
                    return False
                
                # 2. Wenn bereits ein alter Username existiert, LEAVE senden
                if old_username:
                    print(f"[Discovery] Username wird geändert von '{old_username}' zu '{new_username}'...")
                    self.send_leave()
                    print(f"[Discovery] LEAVE gesendet für '{old_username}'")
                    time.sleep(1)  # Kurze Pause
                    
                    # Alten User aus der lokalen Liste entfernen
                    self.ipc_handler.remove_user_by_name(old_username)
                
                # 3. Neuen Username setzen
                self.username = new_username
                
                # 4. JOIN mit neuem Username senden
                self.send_join()
                
                # 5. Sich selbst zur User-Liste hinzufügen
                local_ip = self.config['network'].get('local_ip', '127.0.0.1')
                tcp_port = self.chat_tcp_port
                self.ipc_handler.update_user_list(new_username, local_ip, tcp_port, time.time())
                
                print(f"[Discovery] JOIN gesendet für '{new_username}' - Username-Wechsel abgeschlossen!")
                
                # 6. Discovery-Request senden, um andere Nutzer zu benachrichtigen
                time.sleep(0.5) #Pause
                self.request_discovery() #Discovery anfordern
                
                return True # Erfolgreich geändert
                
            # Error-Handling
            except Exception as e:
                print(f"[Discovery] Fehler beim Ändern des Handles: {e}")
                return False