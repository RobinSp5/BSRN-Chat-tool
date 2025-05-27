# ipc_handler.py – zentrale Steuerung für Netzwerk und Discovery (BSRN-Projekt)

import socket
import threading
import time

# === Discovery-Teilnehmerliste ===
users = {}  # {handle: (ip, port)}

# === Discovery-Handler-Funktion ===
def discovery_loop(to_discovery, from_network, config):
    whois_port = config.get("whoisport", 4000)
    handle = config["handle"]
    peer_port = config["port"]

    # UDP-Socket für Discovery öffnen
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', whois_port))

    print(f"[Discovery] Läuft auf Port {whois_port}")

    # Empfangs-Thread für eingehende Discovery-Nachrichten
    def empfange_discovery():
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode().strip()
                teile = message.split()

                if not teile:
                    continue

                befehl = teile[0]

                # === JOIN empfangen ===
                if befehl == "JOIN" and len(teile) == 3:
                    remote_handle = teile[1]
                    remote_port = int(teile[2])
                    users[remote_handle] = (addr[0], remote_port)
                    print(f"[JOIN] {remote_handle} beigetreten von {addr[0]}:{remote_port}")

                # === LEAVE empfangen ===
                elif befehl == "LEAVE" and len(teile) == 2:
                    remote_handle = teile[1]
                    if remote_handle in users:
                        del users[remote_handle]
                        print(f"[LEAVE] {remote_handle} hat den Chat verlassen")

                # === WHO empfangen – sende KNOWNUSERS zurück ===
                elif befehl == "WHO":
                    antwort = "KNOWNUSERS " + ", ".join(f"{h} {ip} {p}" for h, (ip, p) in users.items())
                    sock.sendto(antwort.encode("utf-8"), addr)
                    print(f"[WHO] Antwort gesendet an {addr}")

            except Exception as e:
                print(f"[Discovery-Fehler]: {e}")

    threading.Thread(target=empfange_discovery, daemon=True).start()

    # Haupt-Loop: Wartet auf Anfragen vom CLI
    while True:
        try:
            cmd = to_discovery.get(timeout=0.5)

            if cmd.startswith("JOIN"):
                sock.sendto(cmd.encode("utf-8"), ('<broadcast>', whois_port))
                print("[Discovery] JOIN gesendet")

            elif cmd.startswith("LEAVE"):
                sock.sendto(cmd.encode("utf-8"), ('<broadcast>', whois_port))
                print("[Discovery] LEAVE gesendet")

            elif cmd == "WHO":
                sock.sendto("WHO".encode("utf-8"), ('<broadcast>', whois_port))
                print("[Discovery] WHO gesendet")

        except Exception:
            continue
        
# === Einstiegspunkt für main.py ===
def ipc_handler(to_network, from_network, to_discovery, config):
    # Starte Discovery-Dienst in einem Thread
    threading.Thread(target=discovery_loop, args=(to_discovery, from_network, config), daemon=True).start()

    # TODO: Weitere Netzwerk-Komponenten wie MSG/IMG können hier ergänzt werden
    while True:
        time.sleep(1)  # Platzhalter-Loop
