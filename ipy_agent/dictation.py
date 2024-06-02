from io import BytesIO
import time
import sounddevice as sd
import numpy as np
from openai import OpenAI
from pydub import AudioSegment
from pynput import keyboard
from pynput.keyboard import Controller
import logging
from threading import Thread

class AudioTranscriber:
    def __init__(self, language='fr', model="whisper-1"):
        self.client = OpenAI()
        self.language = language
        self.model = model

    def transcribe(self, audio_data):
        try:
            audio_data.seek(0)
            transcript = self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_data,
                language=self.language
            )
            return transcript.text
        except Exception as e:
            logging.error(f"Erreur lors de la transcription audio : {e}")
            return ''

class AudioRecorder:
    def __init__(self):
        self.recording = []
        self.stream = None
        self.audio_data = BytesIO()

    def start_recording(self):
        self.recording = []
        try:
            self.stream = sd.InputStream(callback=self.audio_callback, channels=1, samplerate=44100)
            self.stream.start()
        except Exception as e:
            logging.error(f"Erreur lors du démarrage de l'enregistrement : {e}")

    def stop_recording(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            self.save_as_mp3()

    def save_as_mp3(self):
        try:
            scaled = np.int16(np.array(self.recording) * 32767)
            audio_segment = AudioSegment(
                data=scaled.tobytes(),
                sample_width=scaled.dtype.itemsize,
                frame_rate=44100,
                channels=1
            )
            self.audio_data = BytesIO()
            self.audio_data.name="audio.mp3"
            audio_segment.export(self.audio_data, format='mp3')
            

        except Exception as e:
            logging.error(f"Erreur lors de la sauvegarde du fichier audio : {e}")

    def audio_callback(self, indata, frames, time, status):
        if status:
            logging.error(f"Status: {status}")
        self.recording.extend(indata.copy())

class HotKey:

    def __init__(self,hotkey,on_press=lambda :None,on_release=lambda :None):
        self.hotkey=keyboard.HotKey.parse(hotkey)
        self.pressed=False
        self.on_press=on_press
        self.on_release=on_release

    def is_hotkey(self,keys_pressed):
        return all(k in keys_pressed for k in self.hotkey) and all(k in self.hotkey for k in keys_pressed)

    def _on_press(self,keys_pressed):
        if self.is_hotkey(keys_pressed) and not self.pressed:
            self.pressed = True
            self.on_press()

    def _on_release(self,keys_pressed):
        if not self.is_hotkey(keys_pressed) and self.pressed:
            self.pressed = False
            self.on_release()

class HotKeyListener:
    def __init__(self):
        self.hotkeys=[]
        self.keys_pressed = set()
        self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)

    def bind(self,hotkey,on_press=lambda :None, on_release=lambda :None):
        self.hotkeys.append(HotKey(hotkey,on_press=on_press,on_release=on_release))

    def _on_press(self, key):
        self.keys_pressed.add(key)
        for hotkey in self.hotkeys:
            hotkey._on_press(self.keys_pressed)

    def _on_release(self, key):
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)
        for hotkey in self.hotkeys:
            hotkey._on_release(self.keys_pressed)
        
    def start(self):
        self.listener.start()
        try:
            while True:
                if not self.listener.is_alive():
                    self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
                    self.listener.start()
                time.sleep(0.5)
        except KeyboardInterrupt:
            logging.info("Interruption par l'utilisateur.")


def start_dictation():

    def on_press():
        audio_recorder.start_recording()

    def on_release():
        audio_recorder.stop_recording()
        text = audio_transcriber.transcribe(audio_recorder.audio_data)
        write_text(text)  # Simuler l'écriture du texte au niveau du curseur actif.

    def write_text(text):
        keyboard = Controller()
        for char in text:
            keyboard.press(char)
            keyboard.release(char)
            time.sleep(0.005)

    audio_transcriber = AudioTranscriber()
    audio_recorder = AudioRecorder()
    keyboard_listener = HotKeyListener()
    keyboard_listener.bind("<ctrl>+<space>",on_press=on_press, on_release=on_release)

    def listen():
        try:
            keyboard_listener.start()
        except Exception as e:
            logging.error(f"Erreur lors de l'écoute du clavier : {e}")

    listen_thread = Thread(target=listen)
    listen_thread.daemon = True
    listen_thread.start()
