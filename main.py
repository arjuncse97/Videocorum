import sys, os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, Gtk

# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
from gi.repository import GdkX11, GstVideo
import ctypes


class GTK_Main(object):
      
    def __init__(self):
        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        window.set_title("Videocorum")
        window.set_default_size(500, 400)
        window.connect("destroy", Gtk.main_quit, "WM destroy")
        

        vbox = Gtk.VBox(False, 0)
        window.add(vbox)
        
        menu_bar = Gtk.MenuBar()
        hbox = Gtk.HBox()
        hbox.add(menu_bar)
        vbox.pack_start(hbox, False, False, 0)
        menu_bar.show()
        
        menu_bar.append(self.file_submenu())
        menu_bar.append(self.subtitles_submenu())
        menu_bar.append(self.generate_dummy_list_items("Settings"))
        menu_bar.append(self.generate_dummy_list_items("Help"))

        #hbox = Gtk.HBox()
        #vbox.pack_start(hbox, False, False, 0)
        #self.entry = Gtk.Entry()
        #hbox.add(self.entry)
        #self.button = Gtk.Button("Start")
        #hbox.pack_start(self.button, False, False, 0)
        #self.button.connect("clicked", self.start_stop)
        self.movie_window = Gtk.DrawingArea()
        vbox.add(self.movie_window)
        
        hbox = Gtk.HBox()
        button_start = Gtk.Button(stock=Gtk.STOCK_MEDIA_PAUSE)
        hbox.add(button_start)
        button_start.connect("clicked", self.action_pause)
        button_start.show()
        button = Gtk.Button(stock=Gtk.STOCK_MEDIA_STOP)
        hbox.add(button)
        button.connect("clicked", self.action_stop, button_start)
        button.show()
        vbox.pack_start(hbox, False, False, 0)
         
        window.show_all()
        
        self.player = Gst.ElementFactory.make("playbin", "player")
        print(type(self.player))
	print(self.player)
	bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)


    def action_stop(self, widget, button_start):
        self.player.set_state(Gst.State.NULL)
        self.player.set_state(Gst.State.PLAYING)
        self.player.set_state(Gst.State.PAUSED)
        button_start.set_label(Gtk.STOCK_MEDIA_PLAY)

    def action_pause(self, widget):
        if ("pause" in widget.get_label()):
            self.player.set_state(Gst.State.PAUSED)
            widget.set_label(Gtk.STOCK_MEDIA_PLAY)
        else:
            self.player.set_state(Gst.State.PLAYING)
            widget.set_label(Gtk.STOCK_MEDIA_PAUSE)

    def open_file(self, widget, string):
        dialog = Gtk.FileChooserDialog("Open", None,
                Gtk.FileChooserAction.OPEN, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        dialog.set_default_response(Gtk.ResponseType.OK)

        fil = Gtk.FileFilter()
        fil.set_name("Video files")
        fil.add_pattern("*.mp4")
        fil.add_pattern("*.mkv")
        dialog.add_filter(fil)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            name = "file:///" + dialog.get_filename()
            print(name)
            self.player.set_state(Gst.State.NULL)
            self.player.set_property("uri", (name))
            self.filename = name
            #subtitle_add = "file:////home/sumedh/Desktop/se_test.srt"
            #self.player.set_property("suburi", subtitle_add)
            #self.player.set_property("subtitle-font-desc", "Sans, 18")
            #print(subtitle_add)
            self.player.set_state(Gst.State.PLAYING)
        dialog.destroy()

    def open_subtitles(self, widget, string):
        dialog = Gtk.FileChooserDialog(string, None,
                Gtk.FileChooserAction.OPEN, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        dialog.set_default_response(Gtk.ResponseType.OK)

        fil = Gtk.FileFilter()
        fil.set_name("srt")
        fil.add_pattern("*.srt")
        dialog.add_filter(fil)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            name = "file:///" + dialog.get_filename()
            dialog.destroy()
            _, duration = self.player.query_position(Gst.Format.TIME)
            print(duration)
            print(10**10)
            self.player.set_state(Gst.State.READY)
            #self.player.set_property("uri", self.filename)
            self.player.set_property("suburi", name)
            self.player.set_property("subtitle-font-desc", "Sans, 18")
            self.player.set_state(Gst.State.PLAYING)
            #import time
            #time.sleep(4)
            #self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 10**10+duration)

 
    def menuitem_response(self, widget, string):
        print "%s" % string
    
    def file_submenu(self):
        menu = Gtk.Menu()
        menu_items = Gtk.MenuItem("Open..")
        menu.append(menu_items)

        menu_items.connect("activate", self.open_file, "Open..")

        menu_items.show()
        root_menu = Gtk.MenuItem("File")
        root_menu.show()
        root_menu.set_submenu(menu)
        return root_menu

    def subtitles_submenu(self):
        menu = Gtk.Menu()
        menu_items = Gtk.MenuItem("Add Subtitles")
        menu.append(menu_items)

        menu_items.connect("activate", self.open_subtitles, "Subtitles")

        menu_items.show()
        menu_items = Gtk.MenuItem("Generate Subtitles")
        menu.append(menu_items)
        menu_items.connect("activate", self.auto_generate, "auto generate")
        root_menu = Gtk.MenuItem("Subtitles")
        root_menu.show()
        root_menu.set_submenu(menu)
        return root_menu

    def auto_generate(self, widget, name):
        self.auto_generate_subtitles = thread.start_new_thread(self.start_generate, ())
        return
    def generate_dummy_list_items(self, name):
        menu = Gtk.Menu()
        for i in range(3):
            # Copy the names to the buf.
            buf = "Test-undermenu - %d" % i

            # Create a new menu-item with a name...
            menu_items = Gtk.MenuItem(buf)

            # ...and add it to the menu.
            menu.append(menu_items)

            # Do something interesting when the menuitem is selected
            menu_items.connect("activate", self.menuitem_response, buf)

            # Show the widget
            menu_items.show()
        root_menu = Gtk.MenuItem(name)
        root_menu.show()
        root_menu.set_submenu(menu)
        return root_menu



    def start_stop(self, w):
        if self.button.get_label() == "Start":
            filepath = self.entry.get_text().strip()
            if os.path.isfile(filepath):
                filepath = os.path.realpath(filepath)
                self.button.set_label("Stop")
                self.player.set_property("uri", "file://" + filepath)
                self.player.set_state(Gst.State.PLAYING)
            else:
                self.player.set_state(Gst.State.NULL)
                self.button.set_label("Start")
                
    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.player.set_state(Gst.State.NULL)
        elif t == Gst.MessageType.ERROR:
            self.player.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.button.set_label("Start")
            
    def on_sync_message(self, bus, message):
        if message.get_structure().get_name() == 'prepare-window-handle':
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            video_window = self.movie_window.get_property('window')
            if sys.platform == "win32":
                if not video_window.ensure_native():
                    print("Error - video playback requires a native window")
                ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
                ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object]
                drawingarea_gpointer = ctypes.pythonapi.PyCapsule_GetPointer(video_window.__gpointer__, None)
                gdkdll = ctypes.CDLL ("libgdk-3-0.dll")
                imagesink.set_window_handle(gdkdll.gdk_win32_window_get_handle(drawingarea_gpointer))
            else:
                imagesink.set_window_handle(video_window.get_xid())
            #imagesink.set_window_handle(self.movie_window.get_property('window').get_xid())


GObject.threads_init()
Gst.init(None)
GTK_Main()
Gtk.main()
