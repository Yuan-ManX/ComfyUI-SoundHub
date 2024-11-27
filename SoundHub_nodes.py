import os
import hashlib
import numpy as np
import torch
import torchaudio
import folder_paths
import random
from datetime import datetime

class LoadAudio:
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        audio_extensions = ('.wav', '.mp3', '.ogg', '.flac')
        files = [f for f in os.listdir(input_dir) 
                if os.path.isfile(os.path.join(input_dir, f)) 
                and f.lower().endswith(audio_extensions)]
        return {"required": {
                    "audio": (sorted(files), {
                        "file_type": "audio",            
                        "file_select": "audio",           
                        "upload": "audio",               
                        "display": "file"                
                    }),
                    "preview": ("BOOLEAN", {
                        "default": True,
                        "label": "Preview after loading"
                    }),
                    "channels": (["auto", "mono", "stereo"], ),
                    "start_time": ("FLOAT", {
                        "default": 0, 
                        "min": 0, 
                        "max": 10000000, 
                        "step": 0.01,
                        "display": "number"
                    }),
                    "duration": ("FLOAT", {
                        "default": 0, 
                        "min": 0, 
                        "max": 10000000, 
                        "step": 0.01,
                        "display": "number"
                    }),
                    "volume": ("FLOAT", {
                        "default": 1.0,
                        "min": 0.0,
                        "max": 5.0,
                        "step": 0.1,
                        "display": "number"
                    }),
                }}

    CATEGORY = "SoundHub"
    RETURN_TYPES = ("AUDIO", "SAMPLE_RATE")
    RETURN_NAMES = ("audio", "sample_rate")
    FUNCTION = "load_audio"

    def load_audio(self, audio, preview, channels, start_time, duration, volume):
        audio_path = folder_paths.get_annotated_filepath(audio)
        
        waveform, sample_rate = torchaudio.load(audio_path)
        
        if waveform.dtype != torch.float32:
            waveform = waveform.to(torch.float32)
        
        if duration > 0:
            start_frame = int(start_time * sample_rate)
            duration_frames = int(duration * sample_rate)
            waveform = waveform[:, start_frame:start_frame + duration_frames]
        elif start_time > 0:
            start_frame = int(start_time * sample_rate)
            waveform = waveform[:, start_frame:]
        
        if channels == "mono":
            if waveform.size(0) == 2:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
        elif channels == "stereo":
            if waveform.size(0) == 1:
                waveform = waveform.repeat(2, 1)
        
        waveform = waveform * volume
        
        if preview:
            preview_data = {
                "ui": {
                    "audio": {
                        "audio": audio_path,
                        "type": "input"
                    }
                }
            }
            return (waveform, sample_rate, preview_data)
        
        return (waveform, sample_rate)

    @classmethod
    def IS_CHANGED(s, audio, preview, channels, start_time, duration, volume):
        audio_path = folder_paths.get_annotated_filepath(audio)
        m = hashlib.sha256()
        with open(audio_path, 'rb') as f:
            m.update(f.read())
        m.update(str(start_time).encode())
        m.update(str(duration).encode())
        m.update(str(channels).encode())
        m.update(str(volume).encode())
        return m.digest().hex()


class PreviewAudio:
    def __init__(self):
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"
        self.prefix_append = "_temp_" + ''.join(random.choice("abcdefghijklmnopqrstupvxyz") for x in range(5))

    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                    "audio": ("AUDIO",),
                    "sample_rate": ("SAMPLE_RATE",),
                }}
    
    CATEGORY = "SoundHub"
    RETURN_TYPES = ()
    FUNCTION = "preview_audio"
    OUTPUT_NODE = True

    def preview_audio(self, audio, sample_rate):
        # Add basic audio validation
        if audio is None or not isinstance(audio, torch.Tensor):
            raise ValueError("Invalid audio input")
            
        if audio.dim() > 2 or audio.dim() == 0:
            raise ValueError("Audio must be mono or stereo (1 or 2 channels)")
            
        os.makedirs(self.output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"preview{self.prefix_append}_{timestamp}.wav"
        filepath = os.path.join(self.output_dir, filename)
        
        if isinstance(audio, torch.Tensor):
            torchaudio.save(
                filepath,
                audio,
                sample_rate,
                format="wav"
            )

        preview = {
            "audio": filepath,
            "type": self.type
        }
        
        return {"ui": {"audio": preview}}


class SaveAudio:
    def __init__(self):
        # Initialize output directory and settings
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio": ("AUDIO", {"tooltip": "The audio to save."}),
                "sample_rate": ("SAMPLE_RATE", {"tooltip": "The sample rate of the audio."}),
                "filename_prefix": ("STRING", {
                    "default": "ComfyUI_Audio",
                    "tooltip": "The prefix for the file to save. Can include formatting like %date:yyyy-MM-dd%"
                }),
                "format": (["wav", "mp3", "ogg", "flac"], {
                    "default": "wav",
                    "tooltip": "Audio format to save as"
                })
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_audio"
    OUTPUT_NODE = True
    CATEGORY = "SoundHub"
    DESCRIPTION = "Saves the input audio to your ComfyUI output directory."

    def save_audio(self, audio, sample_rate, filename_prefix="ComfyUI_Audio", format="wav", prompt=None, extra_pnginfo=None):
        # Validate audio format
        if format not in ["wav", "mp3", "ogg", "flac"]:
            raise ValueError(f"Unsupported audio format: {format}")
            
        # Validate sample rate
        if sample_rate <= 0:
            raise ValueError("Invalid sample rate")
            
        # Add any prefix append to the filename
        filename_prefix += self.prefix_append
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Get current timestamp for unique filename
        current_time = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        # Build base filename
        filename = f"{filename_prefix}_{current_time}"
        
        # Handle subfolders in filename_prefix
        subfolder = os.path.dirname(filename_prefix) if "/" in filename_prefix else ""
        if subfolder != "":
            # Create subfolder if specified in prefix
            full_output_folder = os.path.join(self.output_dir, subfolder)
            os.makedirs(full_output_folder, exist_ok=True)
        else:
            full_output_folder = self.output_dir
            
        # Ensure unique filename by incrementing counter
        counter = 1
        while True:
            file = f"{filename}_{counter:05}.{format}"
            full_path = os.path.join(full_output_folder, file)
            if not os.path.exists(full_path):
                break
            counter += 1

        # Save the audio file
        if isinstance(audio, torch.Tensor):
            # Ensure audio data is in float32 format
            if audio.dtype != torch.float32:
                audio = audio.to(torch.float32)
            
            # Save audio using torchaudio
            torchaudio.save(
                full_path,
                audio,
                sample_rate,
                format=format
            )

        # Prepare results for UI
        results = [{
            "filename": file,
            "subfolder": subfolder,
            "type": self.type,
            "format": format
        }]

        # Handle metadata if provided
        # Note: Audio metadata handling could be implemented here
        if prompt is not None or extra_pnginfo is not None:
            # TODO: Add metadata handling for audio files
            pass

        # Return results for UI display
        return {"ui": {"audio": results[0]}}

    @classmethod
    def IS_CHANGED(s, audio, sample_rate, filename_prefix, format):
        # Always save a new file
        return float("nan")
