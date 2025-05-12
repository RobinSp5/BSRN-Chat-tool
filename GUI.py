import tkinter as tk
from tkinter import scrolledtext, Entry, Button, Frame

class ChatApp:
    """
    Einfache Chat-Anwendung mit Tkinter, die Textnachrichten anzeigt und
    eine Eingabemaske zum Senden bereitstellt.
    """

    def __init__(self, master):
        """
        Initialisiert die GUI-Komponenten:
         - Titel und Fenstergröße
         - Nachrichtenausgabe als gescrolltes Textfeld (read-only)
         - Eingabefeld und Senden-Button in einem Frame
        """
        self.master = master
        master.title("Simple Chat Tool")       # Fenster-Titel
        master.geometry("600x500")            # Fenster-Größe (Breite x Höhe)

        # Nachrichtenverlauf: gescrolltes Textfeld, nicht editierbar
        self.chat_history = scrolledtext.ScrolledText(
            master,
            wrap=tk.WORD,       # Zeilenumbruch nach Wörtern
            width=70,           # Breite in Zeichen
            height=20,          # Höhe in Zeilen
            state='disabled'    # anfänglich nicht editierbar
        )
        self.chat_history.pack(
            padx=10,            # horizontaler Innenabstand
            pady=10,            # vertikaler Innenabstand
            fill=tk.BOTH,       # füllt sowohl horizontal als auch vertikal
            expand=True         # dehnt sich mit dem Fenster
        )

        # Eingabebereich in einem eigenen Frame
        input_frame = Frame(master)
        input_frame.pack(
            padx=10,
            pady=10,
            fill=tk.X           # füllt nur horizontal
        )

        # Texteingabe für neue Nachrichten
        self.message_entry = Entry(
            input_frame,
            width=50            # Breite in Zeichen
        )
        self.message_entry.pack(
            side=tk.LEFT,       # links im Frame
            expand=True,        # nimmt verbleibenden Platz ein
            fill=tk.X,          # füllt horizontal
            padx=(0, 10)        # Abstand rechts zum Button
        )

        # Button zum Abschicken der Nachricht
        send_button = Button(
            input_frame,
            text="Senden",
            command=self.send_message  # Verknüpfung mit der Methode send_message
        )
        send_button.pack(side=tk.RIGHT)  # rechts im Frame

    def send_message(self):
        """
        Diese Methode wird aufgerufen, wenn der Nutzer auf 'Senden' klickt.
        Hier kann später die Logik implementiert werden, um die Nachricht
        über das Netzwerk zu versenden und ins Chat-Fenster einzufügen.
        """
        # Platzhalter für zukünftige Implementierung
        pass

def main():
    """
    Startet die Tkinter-Hauptschleife und erzeugt das Chat-Fenster.
    """
    root = tk.Tk()             # Hauptfenster erstellen
    chat_app = ChatApp(root)   # Chat-Anwendung initialisieren
    root.mainloop()            # GUI-Event-Schleife starten

if __name__ == "__main__":
    main()  # startet die Anwendung nur, wenn das Skript direkt ausgeführt wird
