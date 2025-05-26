from multiprocessing import Queue
from cli import cli_loop
import subprocess  # ➕ Damit wir discovery.py automatisch starten können

if __name__ == "__main__":
    to_network = Queue()
    from_network = Queue()
    to_discovery = Queue()

    # ➕ Discovery-Dienst automatisch im Hintergrund starten
    subprocess.Popen(["python", "discovery.py"])

    # ➕ CLI starten
    cli_loop(to_network, from_network, to_discovery)
