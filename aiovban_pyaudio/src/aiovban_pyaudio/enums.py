from enum import Enum

import pyaudio

from aiovban.packet.headers.audio import BitResolution


class VBANPyAudioFormatMapping(Enum):
    INT16 = BitResolution.INT16, pyaudio.paInt16
    INT24 = BitResolution.INT24, pyaudio.paInt24
    INT32 = BitResolution.INT32, pyaudio.paInt32
    FLOAT32 = BitResolution.FLOAT32, pyaudio.paFloat32

    def __new__(cls, data, pyaudio_format):
        obj = object.__new__(cls)
        obj.key = obj._value_ = data
        obj.pyaudio_format = pyaudio_format
        return obj
