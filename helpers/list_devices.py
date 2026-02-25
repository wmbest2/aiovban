import pyaudio

p = pyaudio.PyAudio()
print(f"Host API count: {p.get_host_api_count()}")
for i in range(p.get_device_count()):
    print(p.get_device_info_by_index(i))
p.terminate()
