from kokoro import KPipeline
import json
import requests
import sounddevice as sd
import soundfile as sf
from RealtimeSTT import AudioToTextRecorder

def tts(text: str, split_pattern: str | None = r'\n+'):
    generator = pipeline(
        text, 
        voice='pm_santa', # <= change voice here
        speed=1, split_pattern=split_pattern
    )
    for i, (gs, ps, audio) in enumerate(generator):
        print(i)  # Índice do trecho gerado
        print(gs) # Texto original
        # print(ps) # Fonemas
        sd.play(audio, samplerate=24000)
        sd.wait()  # Aguarda o fim da reprodução antes de continuar

def llm_response(text):
    url = "http://localhost:1234/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "gemma-3-1b-it",
        "messages": [
            {"role": "system", "content": "Você é um assistente de IA que responde dúvidas do usuário. Não use emojis ou símbolos especiais"},
            {"role": "user", "content": text}
        ],
        "max_tokens": -1,
        "stream": True
    }
    response = requests.post(url, headers=headers, data=json.dumps(data), stream=True)

    one_line_response = True
    buffer = ""
    for line in response.iter_lines():
        if not line:
            continue
        try:
            token = json.loads(line.decode()[6:])['choices'][0]['delta']['content']
        except Exception as e:
            # print(line.decode())
            continue
        
        if token:
            buffer += token
        if '\n' in token:
            one_line_response = False
            tts(buffer.strip())
            buffer = ""

    if one_line_response:
        tts(buffer.strip())

def wake_word_detected():
    sd.play(audio_data, sample_rate)
    # sd.wait()

def stt():
    print("Wait until it says 'speak now'")
    recorder = AudioToTextRecorder(
        model='base',
        compute_type='auto',
        input_device_index=4,
        language='pt',
        wake_words='alexa',
        on_wakeword_detected=wake_word_detected
    )
    
    while True:
        recorder.text(lambda x: print(x))
        recorder.text(llm_response)

if __name__ == '__main__':
    audio_data, sample_rate = sf.read('audio/wake_word.wav')
    pipeline = KPipeline(lang_code='p', device='cuda')

    stt()
    # llm_response('olá tudo bem?')





    # print(llm_response('olá, tudo bem?'))