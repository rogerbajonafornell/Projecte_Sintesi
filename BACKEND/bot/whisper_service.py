# whisper_service.py
from faster_whisper import WhisperModel

# Carrega el model; pots ajustar "medium" per un model més petit o més gran segons els teus recursos
model = WhisperModel("medium", device="cpu", compute_type="int8")

def transcribe_audio(file_path):
    """
    Transcriu el fitxer d'àudio indicat i detecta automàticament l'idioma.
    Retorna una tupla (transcripció, idioma).
    """
    segments, info = model.transcribe(file_path, beam_size=5)
    transcription = " ".join(segment.text for segment in segments)
    return transcription, info.language
