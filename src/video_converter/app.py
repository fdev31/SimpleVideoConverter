import gi

gi.require_version("Adw", "1")
import sys
from gi.repository import Adw, Gdk, Gtk

from .ui.window import VideoConverterWindow
from .constants import CSS


class VideoConverterApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.example.VideoConverter")
        self.win = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.win = VideoConverterWindow(self)

    def do_activate(self):
        """Activate the application."""
        self.win.present()


def main():
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        css_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
    style_manager = Adw.StyleManager.get_default()
    style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)
    app = VideoConverterApp()
    return app.run(sys.argv)
