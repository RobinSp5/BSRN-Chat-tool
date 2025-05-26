import re

class MessageHandler:
    """
    Verarbeitet geparste SLCP-Nachrichten und leitet sie an das GUI weiter oder gibt sie aus.
    """
    def __init__(self, gui_callback=None):
        """
        Args:
            gui_callback (callable, optional): Funktion, mit der Nachrichten an die GUI übergeben werden.
        """
        self.gui_callback = gui_callback

    def handle(self, parsed: dict):
        """
        Verarbeitet eine Nachricht, die durch SLCPHandler geparst wurde.

        Args:
            parsed (dict): Dictionary mit den Feldern:
                - command: SLCP-Befehlstyp ("MSG", "JOIN", "LEAVE", "IMG", "ERROR", etc.)
                - handle: Absender
                - text / size / raw: je nach Befehl
        """
        cmd = parsed.get('command')

        if cmd == 'MSG':
            sender = parsed.get('handle', 'Unknown')
            text = parsed.get('text', '')
            self._show(f"💬 {sender}: {text}")

        elif cmd == 'JOIN':
            user = parsed.get('handle', 'Unknown')
            self._show(f"🔵 {user} ist dem Chat beigetreten.")

        elif cmd == 'LEAVE':
            user = parsed.get('handle', 'Unknown')
            self._show(f"🔴 {user} hat den Chat verlassen.")

        elif cmd == 'IMG':
            user = parsed.get('handle', 'Unknown')
            size = parsed.get('size', '?')
            self._show(f"🖼️ {user} sendet ein Bild ({size} Bytes)")

        elif cmd == 'ERROR':
            raw = parsed.get('raw', '')
            self._show(f"⚠️ Fehler beim Verarbeiten: {raw}")

        else:
            # Alle anderen oder UNKNOWN
            raw = parsed.get('raw', '')
            self._show(f"❓ Unbekannter Befehl: {raw}")

    def _show(self, message: str):
        """
        Übergibt die formatierte Nachricht an die GUI oder druckt sie.

        Args:
            message (str): Darzulegender Nachrichtentext
        """
        if self.gui_callback:
            self.gui_callback(message)
        else:
            print(message)
