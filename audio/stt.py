from RealtimeSTT import AudioToTextRecorder

def process_text(text):
    print('🟢' + text)

if __name__ == '__main__':
    print("Wait until it says 'speak now'")
    recorder = AudioToTextRecorder(
        model='base',
        compute_type='auto',
        input_device_index=4,
        language='pt',
        wake_words='alexa'
    )
    
    while True:
        recorder.text(process_text)