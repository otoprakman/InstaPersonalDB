import torch
import warnings
from pathlib import Path

# Suppress warnings
warnings.filterwarnings("ignore")

_model = None
_utils = None

def get_vad_model():
    global _model, _utils
    if _model is None:
        # Load Silero VAD
        # force_reload=True can be removed after first successful run if needed
        model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                      model='silero_vad',
                                      force_reload=False,
                                      onnx=False)
        _model = model
        _utils = utils
    return _model, _utils

def check_audio_speech(audio_path, threshold_seconds=3.0):
    """
    Returns True if speech segments total > threshold_seconds.
    """
    model, utils = get_vad_model()
    (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils
    
    try:
        wav = read_audio(str(audio_path))
        speech_timestamps = get_speech_timestamps(wav, model, sampling_rate=16000)
        
        total_duration = 0
        for ts in speech_timestamps:
            # timestamps are in samples (likely 16k rate? verify)
            # Silero read_audio normalizes and returns tensor. 
            # get_speech_timestamps returns dict with start/end in samples.
            start = ts['start']
            end = ts['end']
            duration_samples = end - start
            duration_sec = duration_samples / 16000
            total_duration += duration_sec
            
        print(f"File: {audio_path}, Speech duration: {total_duration:.2f}s")
        return total_duration > threshold_seconds
        
    except Exception as e:
        # Fallback: if VAD fails (e.g. no backend for MP4), assume speech exists 
        # and let the robust Whisper model handle it or fail there.
        print(f"Warning: VAD check failed for {audio_path} ({e}). Defaulting to 'Speech Present'.")
        return True
