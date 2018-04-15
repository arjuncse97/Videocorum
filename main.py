#!/usr/bin/env python

import sys, os, thread, time
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, Gtk, Gdk, GLib


# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
gi.require_version('GstVideo', '1.0')
from gi.repository import GdkX11, GstVideo
import pysrt
import ctypes
import thread
import speech_recognition as sr
import shutil
from pydub import AudioSegment
from pydub.silence import split_on_silence, detect_silence, detect_nonsilent
import multiprocessing, subprocess

r = sr.Recognizer()

second = 1000
threshold = 4 * second
chunk_size = 30 * second
counter = 0



class GTK_Main(object):

    #PLAY_IMAGE = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_BUTTON)
    #PAUSE_IMAGE = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_BUTTON)
      
    #Main Window:
    
    def __init__(self):
        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        window.set_title("Videocorum")
        window.set_default_size(500, 400)
        window.connect("destroy", self.main_quit, "WM destroy")
        

        vbox = Gtk.VBox(False, 0)
        window.add(vbox)
        
        #Menu Bar:
        
        menu_bar = Gtk.MenuBar()
        hbox = Gtk.HBox()
        hbox.add(menu_bar)
        vbox.pack_start(hbox, False, False, 0)
        menu_bar.show()
        
        menu_bar.append(self.file_submenu())
        menu_bar.append(self.subtitles_submenu())
        menu_bar.append(self.generate_dummy_list_items("Settings"))
        menu_bar.append(self.generate_dummy_list_items("Help"))

        hbox = Gtk.HBox()
        vbox.pack_start(hbox, False, False, 0)
        self.movie_window = Gtk.DrawingArea()
        vbox.add(self.movie_window)
       
        hbox = Gtk.HBox()
        self.subtitle_box = Gtk.Label(" ")
        self.subtitle_box.show()
        hbox.add(self.subtitle_box)
        vbox.pack_start(hbox, False, False, 0)

        # SEEK BAR
        
        # self.box = Gtk.Box(orientation = Gtk.Orientation.HORIZONTAL)
        # hbox_slider.add(self.box)
        #creating a slider and calculating its range      
        self.slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1000, 1)
        self.slider.set_draw_value(False)
        self.slider_handler_id = self.slider.connect("value-changed", self.on_slider_seek)
        # self.box.pack_start(self.slider, True, True, 0)
        hbox_slider = Gtk.HBox()
        hbox_slider.add(self.slider)
        vbox.pack_start(hbox_slider, False, False, 0)

        hbox = Gtk.HBox()
        toolbar = Gtk.Toolbar()
        hbox.add(toolbar)
        self.time_label = Gtk.Label()
        self.time_label.set_text("00:00 / 00:00")
        hbox.add(self.time_label)
        # hbox.add(self.slider)
        
        #TASK BAR: PLAY, PAUSE, STOP, FORWARD, REWIND, VOLUME:

        self.play_toolbutton = Gtk.ToolButton()
        self.play_toolbutton.set_label("gtk-media-pause")
        self.play_toolbutton.set_icon_name("gtk-media-pause")
        self.play_toolbutton.connect("clicked", self.action_pause)
        toolbar.add(self.play_toolbutton)

        self.rewind_toolbutton = Gtk.ToolButton()
        self.rewind_toolbutton.set_icon_name("gtk-media-rewind")
        self.rewind_toolbutton.connect("clicked", self.rewind_callback)        
        toolbar.add(self.rewind_toolbutton)

        self.stop_toolbutton = Gtk.ToolButton()
        self.stop_toolbutton.set_label("gtk-media-stop")
        self.stop_toolbutton.set_icon_name("gtk-media-stop")
        self.stop_toolbutton.connect("clicked", self.action_stop)
        toolbar.add(self.stop_toolbutton)

        self.forward_toolbutton = Gtk.ToolButton()
        self.forward_toolbutton.set_icon_name("gtk-media-forward")
        self.forward_toolbutton.connect("clicked", self.forward_callback)
        toolbar.add(self.forward_toolbutton)

        self.fast_button = Gtk.ToolButton()
        self.fast_button.set_label("fast")
        self.fast_button.connect("clicked", self.fast_callback)
        toolbar.add(self.fast_button)

        self.slow_button = Gtk.ToolButton()
        self.slow_button.set_label("slow")
        self.slow_button.connect("clicked", self.slow_callback)
        toolbar.add(self.slow_button)

        # separatortoolitem = Gtk.SeparatorToolItem()
        # toolbar.add(separatortoolitem)
        sink = "autoaudiosink"
        bin = Gst.Bin()
        self.speedchanger = Gst.ElementFactory.make("pitch")
        if self.speedchanger is None:
            print ("You need to install the Gstreamer soundtouch elements for "
                    "play it slowly to. They are part of Gstreamer-plugins-bad. Consult the "
                    "README if you need more information.")
        bin.add(self.speedchanger)
        self.audiosink = Gst.parse_launch(sink)
        #self.audiosink = Gst.ElementFactory.make(sink, "sink")

        bin.add(self.audiosink)
        convert = Gst.ElementFactory.make("audioconvert")
        bin.add(convert)
        self.speedchanger.link(convert)
        convert.link(self.audiosink)
        sink_pad = Gst.GhostPad.new("sink", self.speedchanger.get_static_pad("sink"))
        bin.add_pad(sink_pad)


        self.player = Gst.ElementFactory.make("playbin", "player")
        if len(sys.argv) == 2:
            self.player.set_state(Gst.State.NULL)
            self.player.set_property("uri", "file:///"+sys.argv[1])
            self.filename = sys.argv[1]
            self.player.set_property("audio-sink", bin)
            self.speedchanger.set_property("pitch", 0)
            self.player.set_state(Gst.State.PLAYING)
            widget = 1
            GLib.timeout_add(1000, self.update_slider, widget)
        else:
            self.player.set_property("audio-sink", bin)
            self.speedchanger.set_property("pitch", 0)
        
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)


        self.volume_button = Gtk.VolumeButton()
        self.volume_button.connect("value-changed", self.change_volume)
        self.volume_button.set_value(1)
        hbox.add(self.volume_button)
        vbox.pack_start(hbox, False, False, 0)

        self.pbRate = 1
        self.gen = None
        
        window.show_all()

    def main_quit(self, *args):
        if self.gen:
            self.gen.terminate()
            self.gen.join()
        Gtk.main_quit(args[1])
    
    def change_volume(self, widget, *args):
        if self.player:
            volume = self.volume_button.get_value() * 100
            subprocess.call(["amixer", "-D", "pulse", "sset", "Master", str(volume)+"%"])
        return

    def action_stop(self, widget):
        self.player.set_state(Gst.State.NULL)
        self.player.set_state(Gst.State.PLAYING)
        self.player.set_state(Gst.State.PAUSED)
        # button_start.set_label(Gtk.STOCK_MEDIA_PLAY)
        self.play_toolbutton.set_label(Gtk.STOCK_MEDIA_PLAY)
        self.play_toolbutton.set_icon_name(Gtk.STOCK_MEDIA_PLAY)
        self.slider.set_value(0)

    def action_pause(self, widget):
        if ("pause" in widget.get_label()): # paused! label set to play
            self.play_toolbutton.set_icon_name("gtk-media-play")
            self.player.set_state(Gst.State.PAUSED)
            self.play_toolbutton.set_label("gtk-media-play")
            widget.set_label(Gtk.STOCK_MEDIA_PLAY)
        else: # playing! label set to pause
            self.player.set_state(Gst.State.PLAYING)
            self.play_toolbutton.set_icon_name("gtk-media-pause")
            self.play_toolbutton.set_label("gtk-media-play")
            widget.set_label(Gtk.STOCK_MEDIA_PAUSE) 
            #starting up a timer to check on the current playback value
            GLib.timeout_add(1000, self.update_slider, widget)

    def on_slider_seek(self, widget):       
        seek_time_secs = self.slider.get_value()
        pos_int = seek_time_secs * 1000000000
        self.player.seek_simple(Gst.Format.TIME,  Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, seek_time_secs * Gst.SECOND)
        if(self.pbRate != 1):
            event = Gst.Event.new_seek(self.pbRate, Gst.Format.TIME,
                Gst.SeekFlags.FLUSH|Gst.SeekFlags.ACCURATE,
                Gst.SeekType.SET, pos_int, Gst.SeekType.NONE, 0)
            self.player.send_event(event)
        if self.gen:
            self.gen.terminate()
            self.gen.join()
            self.gen = multiprocessing.Process(target = self.start_generate, args=())
            self.gen.start()
        
    #called periodically by the Glib timer, returns false to stop the timer
    def update_slider(self, widget):
         if ("play" in self.play_toolbutton.get_label()):# if paused
            return False # cancel timeout
         else:
            success, self.duration = self.player.query_duration(Gst.Format.TIME)
            self.total_time = self.convert_ns(self.duration)
            if not success:
                print "Couldn't fetch song duration"
            else:
                self.slider.set_range(0, self.duration / Gst.SECOND)
            #fetching the position, in nanosecs
            success, position = self.player.query_position(Gst.Format.TIME)
            self.current_time = self.convert_ns(position)
            display_time = self.current_time + " / " + self.total_time 
            # print(display_time)
            self.time_label.set_text(display_time)            
            # print(position)
            if not success:
                print "Couldn't fetch current song position to update slider"

            # block seek handler so we don't seek when we set_value()
            self.slider.handler_block(self.slider_handler_id)

            self.slider.set_value(float(position) / Gst.SECOND)

            self.slider.handler_unblock(self.slider_handler_id)

         return True # continue calling every x milliseconds

    #MP4 File Selector:
    def open_file(self, widget, string):
        dialog = Gtk.FileChooserDialog("Open", None,
                Gtk.FileChooserAction.OPEN, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        dialog.set_default_response(Gtk.ResponseType.OK)

        fil = Gtk.FileFilter()
        fil.set_name("Videos")
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
            self.player.set_state(Gst.State.PLAYING)
            GLib.timeout_add(1000, self.update_slider, widget)
        dialog.destroy()
        
    #Subtitle .srt file selector and displaying subtitles:
    def open_subtitles(self, widget, string):
        dialog = Gtk.FileChooserDialog("Open", None,
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

    #Automatic Subtitle Generation:
    def auto_generate(self, widget, name):
        shutil.rmtree('./splitAudio')
        os.mkdir('./splitAudio')
        self.sound_file = AudioSegment.from_file(self.filename[8:])
        self.len_file = len(self.sound_file)
        print("Length of track: " ,self.len_file/second, "seconds")
        self.sub_write_file = pysrt.SubRipFile(encoding='utf-8')
        self.sub_write_file.save(self.filename[8:-4] + ".srt", encoding='utf-8')                    
        
        #self.sub_write_file = multiprocessing.RawValue(pysrt.SubRipFile, self.sub_write_file)
        self.gen = multiprocessing.Process(target = self.start_generate, args=())
        #show = multiprocessing.Process(target = self.show_generated, args=())
        self.gen.start()
        #show.start()
        self.auto_generate_subtitles = thread.start_new_thread(self.show_generated, ())
        #self.auto_generate_subtitles = thread.start_new_thread(self.start_generate, ())
        return

    def show_generated(self):
        state = False
        string = ''
        while True:
            _, time_ns = self.player.query_position(Gst.Format.TIME)
            #self.subtitle_box.set_label(str(subs.at(time_ns/(10**9))[0].text))
            try:
                subs = pysrt.open(self.filename[8:-4]+".srt")
                string = str(subs.at(seconds = int(round(time_ns/(10**9))))[0].text)
            except:
                string = ''
            if self.subtitle_box.get_label() != string:
                print("displaying ", string)
                self.subtitle_box.set_label(string)

    def start_generate(self):
        _, chunk_start = self.player.query_position(Gst.Format.TIME)
        chunk_start = chunk_start / (10**6)# + 10 * second
        chunk_end = chunk_start + chunk_size
        #chunk_start = 0
        while(chunk_end < self.len_file):
            chunk_file = self.sound_file[chunk_start:chunk_end]    
            chunk_start += do_subtitles_generation(self.sub_write_file, self.filename[8:-4], chunk_file, chunk_start)
            chunk_end += chunk_size
        do_subtiles_generation(self.sub_write_file, self.filename[8:-4], self.sound_file[chunk_start:], chunk_start)
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

                
    def on_message(self, bus, message):
        # print "in on_message"
        # print(message.type)
        t = message.type
        if t == Gst.MessageType.EOS:
            self.play_thread_id = None
            self.player.set_state(Gst.State.NULL)
            self.slider.handler_block(self.slider_handler_id)

            self.slider.set_value(float(0) / Gst.SECOND)

            self.slider.handler_unblock(self.slider_handler_id)
            self.play_toolbutton.set_label("gtk-media-play")
            self.play_toolbutton.set_icon_name("gtk-media-play")
            # self.button.set_label("Start")

            self.time_label.set_text("00:00 / 00:00")
        elif t == Gst.MessageType.ERROR:
            self.play_thread_id = None
            self.player.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            #print "Error: %s" % err, debug
            # self.button.set_label("Start")
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
        if(self.pbRate != 1):
            event = Gst.Event.new_seek(self.pbRate, Gst.Format.TIME,
                Gst.SeekFlags.FLUSH|Gst.SeekFlags.ACCURATE,
                Gst.SeekType.SET, seek_ns, Gst.SeekType.NONE, 0)
            self.player.send_event(event)
        GLib.timeout_add(1000, self.update_slider, w)

    def forward_callback(self, w):
        rc, pos_int = self.player.query_position(Gst.Format.TIME)
        seek_ns = pos_int + 10 * 1000000000
        print 'Forward: %d ns -> %d ns' % (pos_int, seek_ns)
        self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, seek_ns)
        if(self.pbRate != 1):
            event = Gst.Event.new_seek(self.pbRate, Gst.Format.TIME,
                Gst.SeekFlags.FLUSH|Gst.SeekFlags.ACCURATE,
                Gst.SeekType.SET, seek_ns, Gst.SeekType.NONE, 0)
            self.player.send_event(event)
        GLib.timeout_add(1000, self.update_slider, w)        

    def fast_callback(self, w):
        self.pbRate += .25
        print "rate changed to ", self.pbRate
        rc, pos_int = self.player.query_position(Gst.Format.TIME)
        print rc, pos_int
        event = Gst.Event.new_seek(self.pbRate, Gst.Format.TIME,
             Gst.SeekFlags.FLUSH|Gst.SeekFlags.ACCURATE,
             Gst.SeekType.SET, pos_int, Gst.SeekType.NONE, 0)
        self.player.send_event(event)        
    
    def slow_callback(self, w):
        self.pbRate -= .25
        print "rate changed to ", self.pbRate
        rc, pos_int = self.player.query_position(Gst.Format.TIME)
        print rc, pos_int
        event = Gst.Event.new_seek(self.pbRate, Gst.Format.TIME,
             Gst.SeekFlags.FLUSH|Gst.SeekFlags.ACCURATE,
             Gst.SeekType.SET, pos_int, Gst.SeekType.NONE, 0)
        self.player.send_event(event)        


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

#Actual Subtitle Generation: 1. Audio Segmentation  2. Speech Recognition   3. Subtitle Generation:
def do_subtitles_generation(sub_write_file, filename, chunk_sound_file, start_chunk):    
    voices = detect_nonsilent(chunk_sound_file, 
        # must be silent for at least half a second
        min_silence_len=50,

        # consider it silent if quieter than -16 dBFS
        silence_thresh=-29	)

    global counter   
    print(voices)
    splits = [0]
    i = 0
    if (len(voices) > 0 and voices[-1][1] == len(chunk_sound_file)):
        del voices[-1]
    for voice in voices:
        if (voice[1] > splits[i] + threshold):
            i += 1
            splits.append(voice[1])

    if (len(voices) > 0 and splits[-1] != voices[-1][1]):
        splits.append(voices[-1][1])
    end_chunk = splits[-1]
    
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
            sub_write_file.save(filename + '.srt', encoding='utf-8')
            print(text)

    return end_chunk


GObject.threads_init()
Gst.init(None)        
GTK_Main()
Gtk.main()
