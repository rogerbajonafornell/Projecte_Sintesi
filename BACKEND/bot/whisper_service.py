# whisper_service.py
from faster_whisper import WhisperModel

# Carrega el model en aquest cas el medium que és el que s'adapta millor al nostre projecte.
model = WhisperModel("medium", device="cpu", compute_type="int8")

def transcribe_audio(file_path):
    """
    Transcriu el fitxer d'àudio indicat i detecta automàticament l'idioma.
    Retorna una tupla (transcripció, idioma).
    """
    segments, info = model.transcribe(file_path, beam_size=5) # beam_sixe: Equilibri velocitat/precisió
    transcription = " ".join(segment.text for segment in segments)
    return transcription, info.language
