from pydub import AudioSegment
from pydub.silence import split_on_silence, detect_silence, detect_nonsilent
import sys, os
import shutil
import speech_recognition as sr
import pysrt

r = sr.Recognizer()

second = 1000
threshold = 4 * second
chunk_size = 30 * second

counter = 0

def do_subtitles_generation(chunk_sound_file, start_chunk):    
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
            file = pysrt.open('my_srt.srt', encoding='utf-8')
            sub = pysrt.SubRipItem()
            sub.index = counter
            counter += 1
            sub.start.milliseconds = start_chunk + splits[i]
            sub.end.milliseconds = start_chunk + splits[i+1]
            sub.text = text
            file.append(sub)
            file.save('my_srt.srt', encoding='utf-8')
            print(text)


shutil.rmtree('./splitAudio')
os.mkdir('./splitAudio')
sound_file = AudioSegment.from_file(sys.argv[1], "mp4")
len_file = len(sound_file)
print("Length of track: " ,len_file/second, "seconds")
file = pysrt.SubRipFile(encoding='utf-8')
file.save('my_srt.srt', encoding='utf-8')
            
chunk_end = chunk_size
while(chunk_end < len_file):
    chunk_file = sound_file[chunk_end - chunk_size:chunk_end]    
    do_subtitles_generation(chunk_file, chunk_end - chunk_size)
    chunk_end += chunk_size

do_subtiles_generation(sound_file[chunk_end - chunk_size:], chunk_end - chunk_size)

