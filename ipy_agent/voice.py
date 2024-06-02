from queue import Queue
from inspect import isgenerator
from threading import Thread
from .utils import tokenize
import time
import io
from pydub import AudioSegment
from pydub.playback import play
from openai import OpenAI

client=OpenAI()

def play_audio(audio):
    if audio is not None and audio.get("bytes"):
        audio_file_like = io.BytesIO(audio["bytes"])
        audio_segment = AudioSegment.from_file(audio_file_like, format="mp3") 
        play(audio_segment)

def text_to_audio(text,voice="shimmer"):
    # Create MP3 audio
    if text.strip():

        mp3_buffer = io.BytesIO()

        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )

        for chunk in response.iter_bytes():
            mp3_buffer.write(chunk)

        mp3_buffer.seek(0)

        audio = AudioSegment.from_file(mp3_buffer,format="mp3").set_channels(1)

        # Extract audio properties
        sample_rate = audio.frame_rate
        sample_width = audio.sample_width
        length=audio.duration_seconds

        # Return the required dictionary
        return {
            "bytes": mp3_buffer.getvalue(),
            "sample_rate": sample_rate,
            "sample_width": sample_width,
            "length": length
        }
    else:
        return None
    
def get_flags(line,specials):
    for begin, end in specials:
        if line.strip().startswith(begin):
            return begin,end
    return None, None

class VoiceProcessor:
    """
    Class handling TTS.
    Uses the speak method as entry point.
    Takes a token stream as input.
    Speaks the stream as it goes.
    Returns a token stream synchronized with speech.
    The thread_decorator is meant for Streamlit compatibility (to decorate Threads with add_script_run_ctx).
    """
    def __init__(self,agent):
        self.agent=agent
        self.line_queue=Queue()
        self.audio_queue=Queue()
        self.output_queue=Queue()
        self.specials=[("```","```"),("\\[","\\]"),("$$","$$")]
        
    def line_splitter(self,stream):
        self.line_queue=Queue()
        def target(stream):
            line=""
            for chunk in stream:
                while '\n' in chunk:
                    parts=chunk.split('\n')
                    line+=parts[0]
                    self.line_queue.put(line)
                    chunk='\n'.join(parts[1:])
                    line=""
                else:
                    line+=chunk
            if line:
                self.line_queue.put(line)
            self.line_queue.put("#END#")

        thread=Thread(target=target,args=(stream,))
        thread.start()

        def reader():
            while not (line:=self.line_queue.get())=="#END#":
                yield line
        return reader()
        
    def line_processor(self,stream):
        self.audio_queue=Queue()
        def target(stream):
            flag=None
            for line in self.line_splitter(stream):
                if self.agent.config.voice_enabled and line:
                    begin,end=get_flags(line,self.specials)
                    if begin and not flag:
                        flag=end
                        audio=None
                    elif flag and line.strip().startswith(flag):
                        flag=None
                        audio=None
                    elif flag:
                        audio=None
                    else:
                        audio=text_to_audio(line,voice=self.agent.config.voice)
                else:
                    audio=None
                self.audio_queue.put((line,audio))
            self.audio_queue.put("#END#")

        thread=Thread(target=target,args=(stream,))
        thread.start()

        def reader():
            while not (content:=self.audio_queue.get())=="#END#":
                yield content
        return reader()
    
    def process(self,line,audio):
        if audio:
            def target1(line):
                tokenized=tokenize(line)
                sleep_time_per_token = 0.95*(audio['length'] / len(tokenized))  # Durée ajustée par token
                for token in tokenized:
                    self.output_queue.put(token)
                    time.sleep(sleep_time_per_token)
                self.output_queue.put('\n')
        else:
            def target1(line):
                for token in tokenize(line):
                    self.output_queue.put(token)
                    time.sleep(0.02)
                self.output_queue.put('\n')
            
        def target2(audio):
            play_audio(audio)
        thread1=Thread(target=target1,args=(line,))
        thread1.start()
        if self.agent.config.voice_enabled:
            thread2=Thread(target=target2,args=(audio,))
            thread2.start()
        thread1.join()
        if self.agent.config.voice_enabled:
            thread2.join()

    def speak(self,stream):
        if self.agent.config.voice_enabled:
            def target(stream):
                self.output_queue=Queue()
                for line,audio in self.line_processor(stream):
                    self.process(line,audio)
                self.output_queue.put("#END#")
            thread=Thread(target=target,args=(stream,))
            thread.start()
            def reader():
                while not (token:=self.output_queue.get())=="#END#":
                    yield token
            return reader()
        else:
            return stream