import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from video_converter.app import main

if __name__ == "__main__":
    sys.exit(main())

