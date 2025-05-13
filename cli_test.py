from multiprocessing import Queue
from cli import cli_loop

if __name__ == "__main__":
    to_network = Queue()
    from_network = Queue()
    to_discovery = Queue()

    cli_loop(to_network, from_network, to_discovery)
 