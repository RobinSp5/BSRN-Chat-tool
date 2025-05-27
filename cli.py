# cli.py - korrigierte Version (ohne den zirkulären Import)
import toml
import threading
import queue
import socket
import os
import sys

# === Globale Liste für bekannte Nutzer (Handle -> (IP, Port)) ===
known_users = {}  # Speichert bekannte Nutzer

# === Zeigt alle verfügbaren Befehle an ===
def print_help():
    print("Verfügbare Befehle:")
    print("  /join                - Dem Chat beitreten")
    print("  /leave               - Chat verlassen")
    print("  /who                 - Teilnehmer im Netzwerk suchen")
    print("  /msg <User> <Text>   - Nachricht an Nutzer senden")
    print("  /img <User> <Pfad>   - Bild an Nutzer senden")
    print("  /set <Schlüssel> <Wert> - Konfiguration ändern und speichern")
    print("  /exit                - Programm beenden")
    print("  /help                - Hilfe anzeigen")

# === Lädt die Konfiguration aus der config.toml Datei ===
def lade_konfiguration(pfad="config.toml"):
    try:
        config = toml.load(pfad)

        # Prüfen, ob Bildordner existiert – wenn nicht: erstellen
        image_dir = config.get("imagepath", "./bilder")
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)

        return config
    except FileNotFoundError:
        print("Die Datei config.toml wurde nicht gefunden. Bitte anlegen oder Pfad prüfen.")
        sys.exit(1)
    except Exception as e:
        print(f"Fehler beim Laden der Konfiguration: {e}")
        sys.exit(1)

# === Verarbeitet KNOWNUSERS-Nachrichten ===
def parse_knownusers(msg):
    global known_users
    if msg.startswith("KNOWNUSERS "):
        eintraege = msg[12:].split(",")
        for eintrag in eintraege:
            teile = eintrag.strip().split()
            if len(teile) == 3:
                handle, ip, port = teile
                known_users[handle] = (ip, int(port))
        print("[INFO] Bekannte Nutzer aktualisiert:", known_users)

# === Wartet kurz auf KNOWUSERS-Antworten und gibt Feedback ===
def handle_who(from_network):
    """Wartet kurz auf KNOWUSERS-Antworten und gibt Feedback."""
    import time
    users = []
    start = time.time()
    while time.time() - start < 2:  # 2 Sekunden auf Antworten warten
        try:
            msg = from_network.get(timeout=0.5)
            if msg.startswith("KNOWUSERS"):
                users.append(msg)
        except queue.Empty:
            continue
    if users:
        print("Bekannte Nutzer im Chat:")
        for user in users:
            print(user)
    else:
        print("Du bist aktuell alleine im Chat.")

# === Sucht ab einem gegebenen Startport den nächsten freien UDP-Port ===
def find_free_udp_port(start_port: int) -> int:
    """Sucht ab einem gegebenen Startport den nächsten freien UDP-Port."""
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                port += 1

# === Fragt den Benutzernamen ab und speichert ihn in der TOML-Datei ===
def benutzername_abfragen_und_speichern(config_path="config.toml"):
    """Fragt den Benutzernamen ab und speichert ihn in der TOML-Datei."""
    try:
        config = toml.load(config_path)
    except Exception:
        # Falls keine config.toml existiert, erstelle eine Standard-Konfiguration
        config = {
            "handle": "",
            "port": 5000,
            "whoisport": 4000,
            "serverport": 5001,
            "imagepath": "./bilder"
        }
    
    # Aktuellen Namen anzeigen (falls vorhanden)
    aktueller_name = config.get("handle", "")
    if aktueller_name:
        print(f"Aktueller Name: {aktueller_name}")
        antwort = input("Möchtest du einen neuen Namen eingeben? (j/n): ").strip().lower()
        if antwort not in ['j', 'ja', 'y', 'yes']:
            return config
    
    # Nach neuem Namen fragen
    while True:
        name = input("Wie möchtest du heißen? ").strip()
        if name:
            config["handle"] = name
            break
        else:
            print("❌ Bitte gib einen gültigen Namen ein!")
    
    # Konfiguration speichern
    try:
        with open(config_path, 'w') as f:
            toml.dump(config, f)
        print(f"✅ Name '{name}' wurde in der Konfiguration gespeichert.")
        return config
    except Exception as e:
        print(f"❌ Fehler beim Speichern der Konfiguration: {e}")
        return config

# === Startet das CLI (Command Line Interface) ===
def cli_loop(to_network, from_network, to_discovery):
    """Hauptschleife der CLI - verarbeitet Benutzereingaben"""
    config = lade_konfiguration()  # Konfiguration laden

    print("Willkommen im SLCP-Chat (CLI-Version)")
    print("Angemeldet als:", config.get("handle", "Unbekannt"))
    print_help()

    # === Thread: empfängt Nachrichten aus dem Netzwerk und zeigt sie an ===
    def nachrichten_empfangen():
        while True:
            try:
                msg = from_network.get(timeout=1)  # Neue Nachricht aus der Empfangs-Queue holen
                if isinstance(msg, str) and msg.startswith("KNOWNUSERS"):
                    parse_knownusers(msg)
                else:
                    print(f"\n[Empfangen] {msg}")
            except queue.Empty:
                continue  # Keine Nachricht vorhanden → erneut warten

    # Startet den Empfangs-Thread im Hintergrund
    threading.Thread(target=nachrichten_empfangen, daemon=True).start()

    # === Haupt-CLI-Eingabeschleife ===
    while True:
        try:
            eingabe = input(">>> ").strip()

            if not eingabe:
                continue  # Leere Eingabe ignorieren

            teile = eingabe.split(" ", 2)  # Befehl aufteilen (max. 3 Teile)
            befehl = teile[0]

            # === Programm beenden bzw. Chat verlassen  ===
            if befehl == "/exit":
                print("Programm wird beendet...")
                break

            # === Dem Chat beitreten (JOIN) ===
            elif befehl == "/join":
                to_discovery.put(f"JOIN {config['handle']} {config['port']}")
                print("JOIN gesendet")

            # === Chat verlassen (LEAVE) ===
            elif befehl == "/leave":
                to_discovery.put(f"LEAVE {config['handle']}")
                for ziel in known_users.values():
                    to_network.put(("LEAVE", ziel, f"LEAVE {config['handle']}"))
                print("LEAVE gesendet")

            # === Teilnehmer im Netzwerk erfragen (WHO) ===
            elif befehl == "/who":
                to_discovery.put("WHO")
                handle_who(from_network)

            # === Nachricht an anderen Nutzer senden (MSG) ===
            elif befehl == "/msg":
                if len(teile) < 3:
                    print("Fehlendes Argument: /msg <User> <Text>")
                else:
                    empfaenger, text = teile[1], teile[2]
                    ziel = known_users.get(empfaenger)
                    if not ziel:
                        print("Empfänger nicht bekannt. Nutze /who.")
                        continue
                    if config.get("away", False):
                        antwort = config.get("autoreply", "Ich bin gerade nicht da.")
                        to_network.put(("MSG", ziel, f"MSG {config['handle']} {antwort}"))
                        print(f"[Abwesenheitsantwort an {empfaenger}]")
                    else:
                        to_network.put(("MSG", ziel, f"MSG {config['handle']} {text}"))
                        print(f"[Gesendet an {empfaenger}]: {text}")

            # === Bild an anderen Nutzer senden (IMG) ===
            elif befehl == "/img":
                if len(teile) < 3:
                    print("Fehlendes Argument: /img <User> <Pfad>")
                else:
                    empfaenger, pfad = teile[1], teile[2]
                    ziel = known_users.get(empfaenger)
                    if not ziel:
                        print("Empfänger nicht bekannt. Nutze /who.")
                        continue
                    try:
                        with open(pfad, "rb") as f:
                            bilddaten = f.read()
                        to_network.put(("IMG", ziel, (f"IMG {config['handle']} {len(bilddaten)}", bilddaten)))
                        print("Bild an", empfaenger, "gesendet – Größe:", len(bilddaten), "Bytes")
                    except FileNotFoundError:
                        print("Bilddatei nicht gefunden:", pfad)

            # === Konfiguration ändern und speichern (/set) ===
            elif befehl == "/set":
                if len(teile) < 3:
                    print("Syntax: /set <Schlüssel> <Wert>")
                else:
                    schluessel, wert = teile[1], teile[2]
                    config[schluessel] = wert
                    try:
                        with open("config.toml", "w") as f:
                            toml.dump(config, f)
                        print(f"Konfig geändert: {schluessel} = {wert}")
                    except Exception as e:
                        print("Fehler beim Schreiben der Konfig:", e)

            # === Hilfe anzeigen ===
            elif befehl == "/help":
                print_help()

            # === Ungültiger Befehl eingegeben ===
            else:
                print("Unbekannter Befehl. Mit /help bekommst du eine Übersicht.")

        except (KeyboardInterrupt, EOFError):
            print("\nBeende CLI...")
            break