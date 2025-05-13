Ein leichtgewichtiges, dezentral organisiertes Chatprogramm, das Text- und Bildnachrichten über ein lokales Netzwerk (LAN) verschicken und empfangen kann. 
Die Anwendung basiert auf dem Simple Local Chat Protocol (SLCP) und wurde im Rahmen eines Hochschulprojekts an der Frankfurt UAS entwickelt.

## 🔧 Features

- Kommunikation über UDP und TCP gemäß SLCP
- Text- und Bildnachrichtenversand im LAN
- Interprozesskommunikation (IPC) zwischen Modulen
- Kommandozeileninterface (CLI) zur Bedienung und Konfiguration
- Discovery-Service zur Erkennung aktiver Nutzer im Netzwerk
- Konfiguration über zentrale TOML-Datei

- ## 🛠️ Technologien

- Programmiersprache: Python 3
- Entwicklungsumgebung: Visual Studio Code
- Bibliotheken: `socket`, `threading`, `toml`, `tkinter`, `os`, `sys`, u.a.
