# cli_test_main.py
from multiprocessing import Queue
from cli import cli_loop  # <--- hier nutzt du die "saubere" Version aus cli.py

if __name__ == "__main__":
    to_network = Queue()
    from_network = Queue()
    to_discovery = Queue()

    config = {
        "handle": "Alice",
        "port": 5000
    }

    cli_loop(to_network, from_network, to_discovery, config)
