import logging
from random import SystemRandom

import pyaudio


def get_device_by_name(instance: pyaudio.PyAudio, name: str):
    for i in range(instance.get_device_count()):
        device_info = instance.get_device_info_by_index(i)
        if device_info["name"] == name:
            return i
    return None


class ProbabilityFilter(logging.Filter):
    probability = 0.10
    cryptogen = SystemRandom()

    def filter(self, record):
        return self.cryptogen.random() < self.probability
