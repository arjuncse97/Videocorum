import sys, os, thread, time
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, Gtk, Gdk

# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
from gi.repository import GdkX11, GstVideo



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
        menu_bar.append(self.generate_dummy_list_items("Subtitles"))
        menu_bar.append(self.generate_dummy_list_items("Settings"))
        menu_bar.append(self.generate_dummy_list_items("Help"))

        hbox = Gtk.HBox()
        vbox.pack_start(hbox, False, False, 0)
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
        
        buttonbox = Gtk.HButtonBox()
        hbox.pack_start(buttonbox, False, False, 0)
        rewind_button = Gtk.Button("Rewind")
        rewind_button.connect("clicked", self.rewind_callback)
        buttonbox.add(rewind_button)
        forward_button = Gtk.Button("Forward")
        forward_button.connect("clicked", self.forward_callback)
        buttonbox.add(forward_button)
        self.time_label = Gtk.Label()
        self.time_label.set_text("00:00 / 00:00")
        hbox.add(self.time_label)
        window.show_all()

        self.player = Gst.Pipeline.new("player")
        source = Gst.ElementFactory.make("filesrc", "file-source")
        demuxer = Gst.ElementFactory.make("oggdemux", "demuxer")
        demuxer.connect("pad-added", self.demuxer_callback)
        self.audio_decoder = Gst.ElementFactory.make("vorbisdec", "vorbis-decoder")
        audioconv = Gst.ElementFactory.make("audioconvert", "converter")
        audiosink = Gst.ElementFactory.make("autoaudiosink", "audio-output")

        for ele in [source, demuxer, self.audio_decoder, audioconv, audiosink]:
            self.player.add(ele)
        source.link(demuxer)
        self.audio_decoder.link(audioconv)
        audioconv.link(audiosink)

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

         
        window.show_all()
        
        self.player = Gst.ElementFactory.make("playbin", "player")
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
        
                
    def play_thread(self):
        play_thread_id = self.play_thread_id
        Gdk.threads_enter()
        self.time_label.set_text("00:00 / 00:00")
        Gdk.threads_leave()

        while play_thread_id == self.play_thread_id:
            try:
                time.sleep(0.2)
                dur_int = self.player.query_duration(Gst.Format.TIME, None)[0]
                if dur_int == -1:
                    continue
                dur_str = self.convert_ns(dur_int)
                Gdk.threads_enter()
                self.time_label.set_text("00:00 / " + dur_str)
                Gdk.threads_leave()
                break
            except:
                pass

        time.sleep(0.2)
        while play_thread_id == self.play_thread_id:
            pos_int = self.player.query_position(Gst.Format.TIME, None)[0]
            pos_str = self.convert_ns(pos_int)
            if play_thread_id == self.play_thread_id:
                Gdk.threads_enter()
                self.time_label.set_text(pos_str + " / " + dur_str)
                Gdk.threads_leave()
            time.sleep(1)

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
        fil.set_name("mp4")
        fil.add_pattern("*.mp4")
        dialog.add_filter(fil)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print(dialog.get_filename())
            self.player.set_state(Gst.State.NULL)
            self.player.set_property("uri", "file://" + dialog.get_filename())
            self.player.set_state(Gst.State.PLAYING)
        dialog.destroy()

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
                self.play_thread_id = thread.start_new_thread(self.play_thread, ())
            else:
            	self.play_thread_id = None
                self.player.set_state(Gst.State.NULL)
                self.button.set_label("Start")
                self.time_label.set_text("00:00 / 00:00")
                
                
    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.play_thread_id = None
            self.player.set_state(Gst.State.NULL)
            self.button.set_label("Start")
            self.time_label.set_text("00:00 / 00:00")
        elif t == Gst.MessageType.ERROR:
            self.play_thread_id = None
            self.player.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            #print "Error: %s" % err, debug
            self.button.set_label("Start")
            self.time_label.set_text("00:00 / 00:00")
            
     
    def demuxer_callback(self, demuxer, pad):
        adec_pad = self.audio_decoder.get_static_pad("sink")
        pad.link(adec_pad)

    def rewind_callback(self, w):
        rc, pos_int = self.player.query_position(Gst.Format.TIME)
        seek_ns = pos_int - 10 * 1000000000
        if seek_ns < 0:
            seek_ns = 0
        print 'Backward: %d ns -> %d ns' % (pos_int, seek_ns)
        self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, seek_ns)

    def forward_callback(self, w):
        rc, pos_int = self.player.query_position(Gst.Format.TIME)
        seek_ns = pos_int + 10 * 1000000000
        print 'Forward: %d ns -> %d ns' % (pos_int, seek_ns)
        self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, seek_ns)

    def convert_ns(self, t):
        s,ns = divmod(t, 1000000000)
        m,s = divmod(s, 60)

        if m < 60:
            return "%02i:%02i" %(m,s)
        else:
            h,m = divmod(m, 60)
            return "%i:%02i:%02i" %(h,m,s)
            
    def on_sync_message(self, bus, message):
        if message.get_structure().get_name() == 'prepare-window-handle':
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_window_handle(self.movie_window.get_property('window').get_xid())


GObject.threads_init()
Gst.init(None)        
GTK_Main()
Gtk.main()
