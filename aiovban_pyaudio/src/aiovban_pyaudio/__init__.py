import importlib.metadata

from .enums import VBANPyAudioFormatMapping
from .player import VBANAudioPlayer
from .sender import VBANAudioSender

try:
    __version__ = importlib.metadata.version("aiovban-pyaudio")
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"
