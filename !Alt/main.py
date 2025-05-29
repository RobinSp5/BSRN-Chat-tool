import toml         # Zum Einlesen der Konfigurationsdatei (config.toml)
import threading    # Um mehrere Dinge gleichzeitig auszuführen (z. B. Server, CLI, Discovery)
import queue        # Für die Kommunikation zwischen den Modulen (Nachrichtenwarteschlangen)
import socket       # Für Netzwerkverbindungen über UDP

# Eigene Module einbinden
from cli import cli_loop, benutzername_abfragen_und_speichern, find_free_udp_port                      # Startet die Kommandozeile (Benutzereingabe)
from ipc_handler import ipc_handler           # Startet die zentrale Netzwerk-Kommunikation
from discovery import main as discovery_main, sende_join_broadcast

users = {}  # Globales Benutzerverzeichnis für die Discovery-Funktionalität

def discovery_loop(to_discovery, from_network, config):
    whois_port = config.get("whoisport", 4000)
    handle = config["handle"]
    peer_port = config["port"]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', whois_port))

    print(f"[Discovery] Läuft auf Port {whois_port}")

    def empfange_discovery():
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode().strip()
                teile = message.split()

                if not teile:
                    continue

                befehl = teile[0]

                if befehl == "JOIN" and len(teile) == 3:
                    remote_handle = teile[1]
                    remote_port = int(teile[2])
                    users[remote_handle] = (addr[0], remote_port)
                    print(f"[JOIN] {remote_handle} beigetreten von {addr[0]}:{remote_port}")

                elif befehl == "LEAVE" and len(teile) == 2:
                    remote_handle = teile[1]
                    if remote_handle in users:
                        del users[remote_handle]
                        print(f"[LEAVE] {remote_handle} hat den Chat verlassen")

                elif befehl == "WHO":
                    antwort = "KNOWNUSERS " + ", ".join(f"{h} {ip} {p}" for h, (ip, p) in users.items())
                    sock.sendto(antwort.encode("utf-8"), addr)
                    print(f"[WHO] Antwort gesendet an {addr}")

            except Exception as e:
                print(f"[Discovery-Fehler]: {e}")

    threading.Thread(target=empfange_discovery, daemon=True).start()

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

# === Hauptfunktion: Startet alle Programmteile ===
def main():
    print("🚀 SLCP Chat wird gestartet...")
    
    # --- 1) Nach Benutzername fragen und Konfiguration laden/speichern ---
    config = benutzername_abfragen_und_speichern()
    
    if not config.get("handle"):
        print("❌ Kein gültiger Name konfiguriert. Programm wird beendet.")
        return

    print(f"✅ Willkommen, {config['handle']}!")

    # --- 2) Ports aus der Konfiguration holen oder Standardwerte setzen ---
    peer_port      = config.get("port", 5000)
    discovery_port = config.get("whoisport", peer_port)
    server_port    = config.get("serverport", peer_port + 1)

    # --- 3) Prüfen, ob Ports frei sind ---
    discovery_port = find_free_udp_port(discovery_port)
    server_port    = find_free_udp_port(server_port)

    print(f"🔍 Discovery läuft auf UDP-Port {discovery_port}")
    print(f"🖥️ Server hört auf UDP-Port {server_port}")

    # --- 4) Queues für Kommunikation zwischen den Komponenten ---
    to_network   = queue.Queue()  # Von CLI an den Netzwerk-Sender
    from_network = queue.Queue()  # Vom Netzwerk an CLI (Empfang)
    to_discovery = queue.Queue()  # Von CLI an Discovery

    # --- 5) Discovery-Dienst im Hintergrund starten ---
    threading.Thread(
        target=discovery_main, 
        args=(discovery_port, config['handle'], peer_port), 
        daemon=True
    ).start()

    # --- 6) JOIN-Broadcast senden ---
    sende_join_broadcast(config['handle'], peer_port, discovery_port)

    # --- 7) IPC-Handler starten (zentraler Netzwerkdienst: Empfangen, Senden, Discovery) ---
    threading.Thread(target=ipc_handler, args=(to_network, from_network, to_discovery, config), daemon=True).start()

    # --- 8) CLI starten (Benutzereingaben & Anzeige) ---
    print("💬 Starte CLI. Mit /help bekommst du alle Befehle.")
    try:
        cli_loop(to_network, from_network, to_discovery)
    except KeyboardInterrupt:
        print("\n👋 CLI beendet durch Benutzer.")
    except Exception as e:
        print(f"❌ Fehler in der CLI: {e}")

# === Einstiegspunkt: Wenn Datei direkt ausgeführt wird ===
if __name__ == "__main__":
    main()
