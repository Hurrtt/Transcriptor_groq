import os
import tempfile
import wave
import pyaudio
import pyperclip
from groq import Groq
from pynput import keyboard
import time
import threading

client = Groq(api_key='API KEY DE GROQ')

def grabar_audio(frecuencia_muestreo=16000, canales=1, fragmento=1024):
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=canales,
        rate=frecuencia_muestreo,
        input=True,
        frames_per_buffer=fragmento)

    print('Presiona la tecla ESPACIO para iniciar la grabación y presiona nuevamente para detenerla...')

    frames = []
    grabando = threading.Event()
    stop_recording = threading.Event()

    def on_press(key):
        if key == keyboard.Key.space:
            if not grabando.is_set():
                # Si no estamos grabando, comenzar grabación
                print('Grabando...')
                grabando.set()
            else:
                # Si ya estamos grabando, detener grabación
                print('Grabación finalizada.')
                grabando.clear()
                stop_recording.set()
                return False  # Detiene el listener

    # Iniciar el listener para detectar pulsaciones de teclas
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    # Esperar a que comience la grabación
    while not grabando.is_set() and not stop_recording.is_set():
        time.sleep(0.01)

    # Grabar mientras esté activado el modo grabación
    while grabando.is_set() and not stop_recording.is_set():
        data = stream.read(fragmento, exception_on_overflow=False)
        frames.append(data)

    listener.join()
    stream.stop_stream()
    stream.close()
    p.terminate()

    return frames, frecuencia_muestreo

def guardar_audio(frames, frecuencia_muestreo):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_temp:
        wf = wave.open(audio_temp.name, "wb")
        wf.setnchannels(1)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
        wf.setframerate(frecuencia_muestreo)
        wf.writeframes(b"".join(frames))
        wf.close()
        return audio_temp.name

def transcribir_audio(ruta_archivo_audio):
    try:
        with open(ruta_archivo_audio, "rb") as archivo:
            transcripcion = client.audio.transcriptions.create(
                file=(os.path.basename(ruta_archivo_audio), archivo.read()),
                model="whisper-large-v3",
                prompt="""El audio es una persona normal trabajando""",
                response_format="text",
                language="es",
            )
        return transcripcion
    except Exception as e:
        print(f'Ocurrió un error: {e}')
        return None

def copiar_transcipcion_al_portapapeles(texto):
    pyperclip.copy(texto)
    print("Texto copiado al portapapeles. Puedes pegarlo con Cmd+V donde lo necesites.")

def main():
    while True:
        frames, frecuencia_muestreo = grabar_audio()
        if not frames:  # Si no hay frames, no continúes
            print("No se grabó audio.")
            continue
            
        archivo_audio_temp = guardar_audio(frames, frecuencia_muestreo)
        print('Transcribiendo...')
        transcripcion = transcribir_audio(archivo_audio_temp)
        if transcripcion:
            print(f'\nTranscripción: {transcripcion}')
            print('Copiando transcripción al portapapeles...')
            copiar_transcipcion_al_portapapeles(transcripcion)
            
        else:
            print('La transcripción falló.')

        os.unlink(archivo_audio_temp)
        print('\nListo para la próxima grabación. Presione ESPACIO para comenzar.')

if __name__ == "__main__":
    main()

