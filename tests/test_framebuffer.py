import pytest
import threading
import time
from aiovban_pyaudio.util import FrameBuffer

def test_framebuffer_basic():
    fb = FrameBuffer(max_frame_count=100, bytes_per_frame=2)
    fb.write(b"\x01\x02\x03\x04", 2)
    
    size, count = fb.size()
    assert size == 4
    assert count == 2
    
    data, read_count, dropped = fb.read(1)
    assert data == b"\x01\x02"
    assert read_count == 1
    assert dropped == 0
    
    size, count = fb.size()
    assert size == 2
    assert count == 1

def test_framebuffer_overflow():
    # Max 2 frames, each 2 bytes
    fb = FrameBuffer(max_frame_count=2, bytes_per_frame=2)
    fb.write(b"\x01\x01", 1)
    fb.write(b"\x02\x02", 1)
    fb.write(b"\x03\x03", 1) # This should push overflow
    
    # When we read 1 frame, it should drop the oldest (01 01) and return the next (02 02)
    data, read_count, dropped = fb.read(1)
    assert dropped == 1
    assert data == b"\x02\x02"
    
    size, count = fb.size()
    assert count == 1 # only 03 03 left

def test_framebuffer_threading():
    fb = FrameBuffer(max_frame_count=1000, bytes_per_frame=1)
    stop_event = threading.Event()
    
    def writer():
        for i in range(100):
            fb.write(b"\x01", 1)
            time.sleep(0.001)
            
    def reader():
        read_total = 0
        while not stop_event.is_set() or fb.size()[1] > 0:
            data, count, dropped = fb.read(5)
            read_total += count
            time.sleep(0.002)
        return read_total

    t1 = threading.Thread(target=writer)
    t1.start()
    
    read_total = []
    def reader_wrapper():
        read_total.append(reader())
        
    t2 = threading.Thread(target=reader_wrapper)
    t2.start()
    
    t1.join()
    stop_event.set()
    t2.join()
    
    # We don't assert exact count because of the sleeps, but we verify no crashes
    assert sum(read_total) <= 100
