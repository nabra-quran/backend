from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from scipy import signal

import numpy as np
import deepspeech
import wave

def read_wav_file(audio_file_path, target_sample_rate=16000):
    with wave.open(audio_file_path, 'rb') as wf:
        current_sample_rate = wf.getframerate()
        audio_data = wf.readframes(wf.getnframes())
    audio = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32767.0
    if current_sample_rate != target_sample_rate:
        audio = signal.resample_poly(audio, target_sample_rate, current_sample_rate)
    audio = np.int16(audio * 32767.0)
    return audio

def transcribe_audio(audio_file_path):
    model = deepspeech.Model('AI Models/Deepspeech/output_graph.pb')
    model.enableExternalScorer('AI Models/Deepspeech/quran.scorer')
    audio = read_wav_file(audio_file_path)
    transcription = model.stt(audio)
    return transcription

class TranscriptionViewSet(viewsets.ViewSet):

    @action(methods=['post'], detail=False)
    def transcribe(self, request):
        audio_file_path = request.data.get('audio_file_path')
        if not audio_file_path:
            return Response({'error': 'audio_file_path not provided'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            predictions_text = transcribe_audio(audio_file_path)
            return Response({'predictions_text': predictions_text}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
