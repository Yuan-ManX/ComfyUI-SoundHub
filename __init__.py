from .SoundHub_nodes import LoadAudio, PreviewAudio, SaveAudio

NODE_CLASS_MAPPINGS = {
    "Load Audio": LoadAudio,
    "Save Audio": SaveAudio,
    "Preview Audio": PreviewAudio
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadAudio": "Load Audio",
    "SaveAudio": "Save Audio",
    "PreviewAudio": "Preview Audio"
}


__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
