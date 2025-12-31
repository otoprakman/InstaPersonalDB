import os
import easyocr
from faster_whisper import WhisperModel
from pathlib import Path
from src.filters import check_audio_speech

# Global models to avoid reloading
_whisper_model = None
_ocr_reader = None

def get_whisper():
    global _whisper_model
    if _whisper_model is None:
        # Int8 quantization for CPU speed
        _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    return _whisper_model

def get_ocr():
    global _ocr_reader
    if _ocr_reader is None:
        _ocr_reader = easyocr.Reader(['en'], gpu=False) # CPU mode
    return _ocr_reader

def transcribe(audio_path):
    model = get_whisper()
    segments, info = model.transcribe(str(audio_path), beam_size=5)
    
    text = ""
    for segment in segments:
        text += segment.text + " "
    return text.strip()

def ocr_image(image_path):
    reader = get_ocr()
    result = reader.readtext(str(image_path), detail=0)
    return " ".join(result)

def process_pipeline(shortcode, raw_dir="data/raw"):
    """
    Process a single post folder:
    1. Find media files.
    2. Transcription (if audio & speech).
    3. OCR (if image).
    4. Read caption (from .txt if instaloader saved it).
    Returns a dict with combined text and metadata.
    """
    post_path = Path(raw_dir) / shortcode
    if not post_path.exists():
        return None
        
    combined_text = []
    
    # 1. Caption
    caption_files = list(post_path.glob("*.txt"))
    for cf in caption_files:
        try:
            with open(cf, 'r', encoding='utf-8') as f:
                combined_text.append(f.read())
        except:
            pass
            
    # 2. Images (OCR)
    # Instaloader saves as .jpg
    image_files = list(post_path.glob("*.jpg"))
    for img in image_files:
        try:
            txt = ocr_image(img)
            if txt:
                combined_text.append(f"[Image Text]: {txt}")
        except Exception as e:
            print(f"OCR Error {img}: {e}")

    # 3. Audio/Video
    # Instaloader saves video as .mp4
    video_files = list(post_path.glob("*.mp4"))
    
    # We might need to select an image for the UI if none exist (video only post)
    generated_images = []

    for vid in video_files:
        # A. Frame Extraction & OCR
        try:
            import cv2
            frame_path = vid.with_name(f"{vid.stem}_keyframe.jpg")
            
            # Extract if not exists
            if not frame_path.exists():
                cap = cv2.VideoCapture(str(vid))
                if cap.isOpened():
                    # Check first frame
                    ret, frame = cap.read()
                    if ret:
                        cv2.imwrite(str(frame_path), frame)
                    cap.release()
            
            # If successfully created/exists, OCR it
            if frame_path.exists():
                generated_images.append(frame_path)
                txt = ocr_image(frame_path)
                if txt:
                   combined_text.append(f"[Video Overlay Text]: {txt}")
        except Exception as e:
            print(f"Frame Extraction/OCR Error {vid}: {e}")

        # B. Audio Transcription
        try:
            # Need to separate audio? faster-whisper handles mp4 files directly via ffmpeg
            if check_audio_speech(vid):
                print(f"Transcribing {vid}...")
                txt = transcribe(vid)
                if txt:
                    # Save transcription to file
                    try:
                        transcription_path = vid.with_name(f"{vid.stem}_transcript.txt")
                        with open(transcription_path, "w", encoding="utf-8") as f:
                            f.write(txt)
                        print(f"Saved transcript to {transcription_path}")
                    except Exception as e:
                        print(f"Could not save transcript file: {e}")

                    combined_text.append(f"[Audio Transcript]: {txt}")
            else:
                print(f"Skipping transcription for {vid} (No speech detected)")
        except Exception as e:
            print(f"Transcription Error {vid}: {e}")
            
    final_text = "\n".join(combined_text)
    
    # Prioritize original images, then generated frames
    final_image = None
    if image_files:
        final_image = image_files[0]
    elif generated_images:
        final_image = generated_images[0]
    
    return {
        "shortcode": shortcode,
        "content": final_text,
        "image_path": str(final_image) if final_image else None
    }
