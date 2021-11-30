"""

O método process_raw do script pocketsphinx.py, localizado em:
/usr/local/lib/python3.7/dist-packages/pocketsphinx/pocketsphinx.py
deve ser substituído pelo método presente nesse arquivo.

Além disso, no cabeçalho desse script, devem ser inseridas as bibliotecas
e variáveis utilizadas aqui (entre ###)

"""

###

import scipy.io.wavfile as wav
import numpy as np

capture = [False]
counter = 0
ts = 3
frames = []

###

def process_raw(self, SDATA, no_search, full_utt):
    global counter
    global capture
    global frames

    if capture[0]:
        print("Capturing...")
        counter += 1
        if counter < (ts*17):
            c_data = bytes(SDATA)
            frames.append(np.frombuffer(c_data, dtype=np.int16))

        else:
            audio_decoded = np.hstack(frames)
            wav.write("sphx_capture.wav", 16000, audio_decoded)
            print("Writing audio...")
            capture[0] = False
            frames = []
            counter = 0

    """process_raw(Decoder self, char const * SDATA, bool no_search, bool full_utt) -> int"""
    return _pocketsphinx.Decoder_process_raw(self, SDATA, no_search, full_utt)
