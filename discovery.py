import socket           # Modul für Netzwerkkommunikation (z. B. UDP-Sockets)
import threading        # Ermöglicht parallele Ausführung (z. B. WHO senden & Nachrichten empfangen gleichzeitig)
import time             # Wird benötigt für Pausen (Sleep) zwischen WHO-Nachrichten
import toml             # Ermöglicht das Einlesen von .toml-Konfigurationsdateien
import sys              # Wird genutzt um das Programm kontrolliert zu beenden

# ======= TOML-KONFIGURATION LADEN ========
CONFIG_PATH = "config.toml"  # Pfad zur Konfigurationsdatei

try:
    config = toml.load(CONFIG_PATH)  # Konfigurationsdatei laden

    # Einzelne Werte aus der Datei lesen (flache Struktur)
    HANDLE = config["handle"]                     # Benutzername (Handle)
    PORT = config["port"]                         # Eigener UDP-Port
    WHOISPORT = config["whoisport"]               # Port für Discovery-Broadcast
    AUTOREPLY = config["autoreply"]               # Abwesenheitsnachricht
    IMAGEPATH = config["imagepath"]               # Speicherort für empfangene Bilder
    AWAY = config["away"]                         # Abwesenheitsstatus (True/False)
except Exception as e:
    print(f"Fehler beim Laden der Konfiguration: {e}")
    sys.exit(1)  # Programm beenden bei Fehlern in der Konfiguration

# ======= SLCP-NACHRICHTENBAUSTEINE =========
# Erzeugt SLCP-konforme Textnachrichten zur Kommunikation

def slcp_join():
    return f"JOIN {HANDLE} {PORT}"  # JOIN: Meldet sich im Netzwerk an

def slcp_leave():
    return f"LEAVE {HANDLE}"         # LEAVE: Meldet sich vom Netzwerk ab

def slcp_who():
    return "WHO"                      # WHO: Anfrage nach bekannten Nutzern

# - NUTZERLISTE 
users = {}  # Speichert bekannte Nutzer in Form: {handle: (ip, port)}

# - EINGEHENDE NACHRICHTEN VERARBEITEN 

def handle_message(message, addr, sock):
    teile = message.strip().split()  # Nachricht in Einzelteile zerlegen
    if not teile:
        return  # Leere Nachricht ignorieren

    befehl = teile[0]  # Der erste Teil ist der Befehl (JOIN, LEAVE, WHO)

    if befehl == "JOIN" and len(teile) == 3:
        handle = teile[1]  # Nutzername
        port = int(teile[2])  # Port des Nutzers
        users[handle] = (addr[0], port)  # IP-Adresse aus Absender + Port aus Nachricht
        print(f"[JOIN] {handle} ist beigetreten von {addr[0]}:{port}")

    elif befehl == "LEAVE" and len(teile) == 2:
        handle = teile[1]
        if handle in users:
            del users[handle]  # Nutzer aus Liste entfernen
            print(f"[LEAVE] {handle} hat den Chat verlassen")

    elif befehl == "WHO":
        # Antwort zusammenbauen mit allen bekannten Nutzern
        antwort = "KNOWUSERS " + ", ".join(f"{h} {ip} {p}" for h, (ip, p) in users.items())
        sock.sendto(antwort.encode("utf-8"), addr)  # Antwort an Fragenden senden
        print(f"[WHO] Antwort gesendet an {addr[0]}:{addr[1]}")


 #   elif befehl == "KNOWUSERS": nicht für den Discovery-Dienst relevant

 #(erstmal auslassen, weil Terminal sonst mit [UNBEKANNT]-NAchichten überflutet) 
 #   else:
 #      print(f"[UNBEKANNT] Nachricht ignoriert: {message}")  # Unbekannter Befehl

# - EINGEHENDE NACHRICHTEN EMPFANGEN 

def listen_for_messages(sock):
    """Empfängt dauerhaft UDP-Nachrichten und leitet sie zur Verarbeitung weiter"""
    while True:
        try:
            data, addr = sock.recvfrom(1024)  # Höre auf Nachrichten (max 1024 Byte)
            message = data.decode()           # Bytes zu String umwandeln
            print(f"[Discovery] Nachricht von {addr}: {message}")
            handle_message(message, addr, sock)  # Nachricht verarbeiten
        except Exception as e:
            print(f"[Fehler beim Empfangen]: {e}")

# - PERIODISCH WHO SENDEN 

def send_periodic_who(sock, target):
    """Sendet regelmäßig WHO-Anfragen per Broadcast"""
    while True:
        sock.sendto(slcp_who().encode(), target)  # WHO senden
        print("[WHO] WHO-Nachricht gesendet")
        time.sleep(5)  # Harte 5-Sekunden-Intervalle für diesen minimalen Dienst

# - HAUPTPROZESS DES DISCOVERY-DIENSTES 

def main():
    # UDP-Socket erstellen
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP-Socket
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Broadcast aktivieren
    sock.bind(('', WHOISPORT))  # An allen IP-Adressen auf whoisport lauschen

    broadcast_addr = ("255.255.255.255", WHOISPORT)  # Zieladresse für Broadcast

    # JOIN-Nachricht beim Start verschicken
    sock.sendto(slcp_join().encode(), broadcast_addr)
    print("[JOIN] JOIN-Nachricht gesendet")

    # Starte WHO-Sende-Thread
    threading.Thread(target=send_periodic_who, args=(sock, broadcast_addr), daemon=True).start()

    # Haupt-Listener-Schleife starten
    try:
        listen_for_messages(sock)  # Empfängt und verarbeitet eingehende UDP-Nachrichten
    except KeyboardInterrupt:
        print("[Beende Discovery-Dienst]")
        sock.sendto(slcp_leave().encode(), broadcast_addr)  # LEAVE-Nachricht verschicken
        sock.close()  # Socket schließen

# - PROGRAMMEINSTIEG 
if __name__ == "__main__":
    main()  # Starte Discovery-Dienst
