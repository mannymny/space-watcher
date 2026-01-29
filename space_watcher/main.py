from space_watcher.infrastructure.error_log import log_error
from space_watcher.presentation.gui import run_gui

def main():
    try:
        run_gui()
    except Exception as e:
        log_error(e, context="main")
        raise

if __name__ == "__main__":
    main()
