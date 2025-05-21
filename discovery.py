import socket           # Für Netzwerkkommunikation (UDP)
import threading        # Für paralleles Senden von WHO-Nachrichten
import time             # Für Sleep-Funktion zwischen den WHO-Nachrichten
import toml             # Zum Einlesen der Konfigurationsdatei
import sys              # Um das Programm bei Fehlern sauber zu beenden

# ======= TOML-KONFIGURATION LADEN ========
CONFIG_PATH = "config.toml"

try:
    config = toml.load(CONFIG_PATH)  # Konfigurationsdatei einlesen

    # Konfigurationswerte auslesen
    USERNAME = config["user"]["name"]
    PORT = config["network"]["port"]
    BROADCAST_IP = config["network"]["broadcast"]
    DISCOVERY_INTERVAL = config["discovery"]["interval"]
except Exception as e:
    print(f"Fehler beim Laden der Konfiguration: {e}")
    sys.exit(1)  # Bei Fehlern das Programm beenden

# ======= SLCP-NACHRICHTENBAUSTEINE =========

def slcp_join():
    return f"JOIN {USERNAME}"

def slcp_leave():
    return f"LEAVE {USERNAME}"

def slcp_who():
    return "WHO"

# ======= EINGEHENDE NACHRICHTEN EMPFANGEN ========

def listen_for_messages(sock):
    """Liest kontinuierlich UDP-Nachrichten aus dem Netzwerk"""
    while True:
        try:
            data, addr = sock.recvfrom(1024)  # Empfange UDP-Paket
            message = data.decode()
            print(f"[Discovery] Nachricht von {addr}: {message}")
        except Exception as e:
            print(f"[Fehler beim Empfangen]: {e}")

# ======= PERIODISCH WHO SENDEN =========

def send_periodic_who(sock, target):
    """Sendet regelmäßig WHO-Broadcasts, um neue Peers zu entdecken"""
    while True:
        sock.sendto(slcp_who().encode(), target)
        time.sleep(DISCOVERY_INTERVAL)

# ======= HAUPTPROZESS DES DISCOVERY-DIENSTES ========

def main():
    # UDP-Socket erstellen
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Ermöglicht Broadcast
    sock.bind(('', PORT))  # Lauscht auf dem angegebenen Port (alle Interfaces)

    broadcast_addr = (BROADCAST_IP, PORT)  # Zieladresse für Broadcasts

    # JOIN-Nachricht direkt beim Start senden
    sock.sendto(slcp_join().encode(), broadcast_addr)

    # Thread starten, der regelmäßig WHO sendet
    threading.Thread(target=send_periodic_who, args=(sock, broadcast_addr), daemon=True).start()

    # Empfangsschleife starten
    try:
        listen_for_messages(sock)
    except KeyboardInterrupt:
        print("[Beende Discovery-Dienst]")
        sock.sendto(slcp_leave().encode(), broadcast_addr)  # LEAVE-Nachricht senden
        sock.close()

# ======= PROGRAMMEINSTIEG ========
if __name__ == "__main__":
    main()
