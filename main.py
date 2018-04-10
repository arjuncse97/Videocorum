import sys, os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, Gtk

# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
from gi.repository import GdkX11, GstVideo
import pysrt
import ctypes
import thread
import speech_recognition as sr
import shutil
from pydub import AudioSegment
from pydub.silence import split_on_silence, detect_silence, detect_nonsilent
import multiprocessing

r = sr.Recognizer()

second = 1000
threshold = 4 * second
chunk_size = 30 * second

counter = 0



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
        self.subtitle_box = Gtk.Label("afkj")
        #self.subtitle_box.set_text("ladfjksklajds")
        self.subtitle_box.show()
        hbox.add(self.subtitle_box)
        vbox.pack_start(hbox, False, False, 0)

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
            #name = "file:///" + dialog.get_filename()
            name = dialog.get_filename()
            self.subtitle_name = name
            dialog.destroy()
            thread.start_new_thread(self.start_subtitles, ())
            #import time
            #time.sleep(4)
            #self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 10**10+duration)

    def start_subtitles(self):
        subs = pysrt.open(self.subtitle_name)
        state = False
        string = ''
        while True:
            _, time_ns = self.player.query_position(Gst.Format.TIME)
            #self.subtitle_box.set_label(str(subs.at(time_ns/(10**9))[0].text))
            try:
                string = str(subs.at(seconds = int(round(time_ns/(10**9))))[0].text)
            except:
                string = ''
            if self.subtitle_box.get_label() != string:
                self.subtitle_box.set_label(string)

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
        shutil.rmtree('./splitAudio')
        os.mkdir('./splitAudio')
        self.sound_file = AudioSegment.from_file(self.filename[8:], "mp4")
        self.len_file = len(self.sound_file)
        print("Length of track: " ,self.len_file/second, "seconds")
        self.sub_write_file = pysrt.SubRipFile(encoding='utf-8')
        self.sub_write_file.save(self.filename[8:-4] + ".srt", encoding='utf-8')                    
        
        self.sub_write_file = multiprocessing.RawValue(pysrt.SubRipFile, self.sub_write_file)
        gen = multiprocessing.Process(target = self.start_generate, args=())
        #show = multiprocessing.Process(target = self.show_generated, args=())
        gen.start()
        #show.start()
        self.auto_generate_subtitles = thread.start_new_thread(self.show_generated, ())
        #self.auto_generate_subtitles = thread.start_new_thread(self.start_generate, ())
        return

    def show_generated(self):
        subs = self.sub_write_file.value
        state = False
        string = ''
        while True:
            _, time_ns = self.player.query_position(Gst.Format.TIME)
            #self.subtitle_box.set_label(str(subs.at(time_ns/(10**9))[0].text))
            try:
                string = str(subs.at(seconds = int(round(time_ns/(10**9))))[0].text)
            except:
                string = ''
            if self.subtitle_box.get_label() != string:
                print("displaying ", string)
                self.subtitle_box.set_label(string)

    def start_generate(self):
        chunk_end = chunk_size
        while(chunk_end < self.len_file):
            chunk_file = self.sound_file[chunk_end - chunk_size:chunk_end]    
            do_subtitles_generation(self.sub_write_file, chunk_file, chunk_end - chunk_size)
            chunk_end += chunk_size
        do_subtiles_generation(self.sub_write_file, self.sound_file[chunk_end - chunk_size:], chunk_end - chunk_size)
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
                Gdk.threads_start()
                if not video_window.ensure_native():
                    print("Error - video playback requires a native window")
                ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
                ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object]
                drawingarea_gpointer = ctypes.pythonapi.PyCapsule_GetPointer(video_window.__gpointer__, None)
                gdkdll = ctypes.CDLL ("libgdk-3-0.dll")
                Gdk.treads_stop()
                imagesink.set_window_handle(gdkdll.gdk_win32_window_get_handle(drawingarea_gpointer))
            else:
                imagesink.set_window_handle(video_window.get_xid())
            #imagesink.set_window_handle(self.movie_window.get_property('window').get_xid())

def do_subtitles_generation(sub_write_file,chunk_sound_file, start_chunk):    
    voices = detect_nonsilent(chunk_sound_file, 
        # must be silent for at least half a second
        min_silence_len=50,

        # consider it silent if quieter than -16 dBFS
        silence_thresh=-29	)

    global counter   
    print(voices)
    splits = [0]
    i = 0
    for voice in voices:
        if (voice[1] > splits[i] + threshold):
            i += 1
            splits.append(voice[1])

    splits.append(chunk_size)
    print(splits)

    print("Split complete")

    for i in range(len(splits) - 1):
        out_file = ".//splitAudio//chunk{0}.wav".format(i)
        print("exporting", out_file)
        chunk_sound_file[splits[i]:splits[i+1]].export(out_file, format="wav")
        with sr.AudioFile(out_file) as source:
            audio = r.record(source)
            text = r.recognize_sphinx(audio)
            #self.sub_write_file = pysrt.open(self.filename[8:-4]+".srt", encoding='utf-8')
            sub = pysrt.SubRipItem()
            sub.index = counter
            counter += 1
            sub.start.milliseconds = start_chunk + splits[i]
            sub.end.milliseconds = start_chunk + splits[i+1]
            sub.text = text
            sub_write_file.append(sub)
            #self.sub_write_file.save('my_srt.srt', encoding='utf-8')
            print(text)


GObject.threads_init()
Gst.init(None)
GTK_Main()
Gtk.main()
