from gi.repository import Gio, GObject


def get_ItemList(orig, namegetter):
    store = Gio.ListStore.new(ListItem)
    for codec in orig:
        store.append(ListItem(namegetter(codec), codec))
    return store


class ListItem(GObject.Object):
    __gtype_name__ = "ListItem"

    def __init__(self, display_name, real_value):
        super().__init__()
        self._display = display_name
        self._value = real_value

    @GObject.Property(type=str)
    def display(self):
        return self._display

    @GObject.Property(type=str)
    def value(self):
        return self._value
