# Simple LAN Chat (SLCP)

Ein leichtgewichtiges, dezentral organisiertes Chatprogramm für Text- und Bildnachrichten im lokalen Netzwerk (LAN). Entwickelt im Rahmen eines Hochschulprojekts an der Frankfurt UAS auf Basis des Simple Local Chat Protocol (SLCP).

---

## 🔧 Features

- **SLCP-Kommunikation**  
  - UDP-Broadcast: JOIN, LEAVE, WHO  
  - TCP-Verbindungen: zuverlässige Bildübertragung (IMG)  
- **Text- & Bildnachrichten**  
- **Interprozesskommunikation (IPC)**  
  - Prozesse für UI, Netzwerk & Discovery  
  - Thread-safe Queues für Datenaustausch  
- **Kommandozeilen-Interface (CLI)**  
  - Nachrichten senden/empfangen  
  - Konfigurationswerte bearbeiten  
- **Discovery-Service**  
  - Erkennung und Pflege aktiver Peers  
- **Zentrale Konfiguration**  
  - `config.toml` mit Netzwerk-, UI- und Nutzer-Einstellungen  
  - Bei Programmstart: interaktive CLI-Eingabe oder GUI-Eingabe (z. B. Benutzername)  

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
