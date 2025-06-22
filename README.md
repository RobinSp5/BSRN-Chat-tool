# Simple LAN Chat (SLCP)

Ein leichtgewichtiges, dezentral organisiertes Chatprogramm für Text- und Bildnachrichten im lokalen Netzwerk (LAN). Nutzbar entweder via Kommandozeilen-Interface (CLI) oder grafischer Benutzeroberflaeche (GUI). Entwickelt im Rahmen eines Hochschulprojekts an der Frankfurt UAS auf Basis des Simple Local Chat Protocol (SLCP).

---

## 🔧 Features

- Versenden und Empfangen von Nachrichten im lokalen Netzwerk
- Versenden von Nachrichten an alle im Netzwerk
- Direktnachrichten
- CLI oder GUI Oberfläche
- Bearbeiten der config.toml während Nutzung der Software
- Autoreply Modus (aktivierung durch Timer oder manuell)


---

## 🛠️ Technologien & Abhängigkeiten

- **Sprache:** Python 3.8+  
- **Entwicklungsumgebung:** Visual Studio Code  
- **Bibliotheken:**  
  - `socket` (UDP/TCP)  
  - `threading` / `queue` (Nebenläufigkeit & IPC)  
  - `toml` (Laden/Speichern der Konfiguration)  
  - `tkinter` (optionales GUI)  
  - `os`, `sys`, `time` (System- und Timing-Utilities)  

---

## Start & Installation

1. Python 3.8 oder höher installieren

   Stelle sicher, dass Python korrekt installiert ist:
   ```
   python --version
   ```

2. Abhängigkeiten installieren

   Installiere die benötigten Bibliotheken:
   ```
   pip install toml
   ```

   Für die GUI wird zusätzlich tkinter benötigt:

   - unter Ubuntu:
     ```
     sudo apt install python3-tk
     ```

3. Programm starten

   - GUI-Version:
     ```
     python gui.py
     ```

   - CLI-Version:
     ```
     python main.py
     ```

4. Hinweise

   - Die Konfiguration wird aus der Datei config.toml gelesen bzw bei Programmstart angepasst.
   - Im CLI können sämtliche Funktionen über Befehle ausgeführt werden (siehe Abschnitt „CLI-Befehle“).

---

## CLI-Befehle

- /join <name>              - Chat beitreten (JOIN senden)
- /who                      - Aktive Nutzer abfragen (WHO senden)
- /msg <text>               - Nachricht an alle senden
- /pm <user> <msg>          - Private Nachricht senden
- /img <user> <pfad>        - Bild privat senden
- /show_config              - Aktuelle Konfiguration anzeigen
- /edit_config <key> <val>  - Konfiguration bearbeiten (z.B. handle)
- /quit                     - LEAVE senden & beenden

---

## Projektdateien – Kurzbeschreibung
- main.py                   - Einstiegspunkt, startet alle Komponenten & lädt Konfiguration.
- cli.py                    - Kommandozeileninterface, verarbeitet Nutzerbefehle.
- gui.py                    - Einfache grafische Benutzeroberfläche.
- chat_client.py            - Versendet Nachrichten und Bilder (TCP).
- chat_server.py            - Empfängt Nachrichten und Bilder (TCP).
- discovery.py              - Discovery-Dienst (UDP, Port 4000) zur Nutzererkennung.
- ipc_handler.py            - Interprozesskommunikation & Datenverwaltung.
- config.toml               - Zentrale Konfigurationsdatei (Username, Ports, etc.).

---

## Architekturuebersicht
<img width="392" alt="Image" src="https://github.com/user-attachments/assets/78bc2fcb-8c57-450d-8718-92f88720b450" />a