from aiovban.packet.headers.service import VBANServiceHeader, ServiceType
import struct

def test_header_pack():
    header = VBANServiceHeader(
        function=0x01,
        service=ServiceType.RTPacketRegister,
        additional_info=0xFF,
        streamname="TestStream"
    )
    packed = header.pack()
    print(f"Packed Header Hex: {packed.hex()}")
    # VBAN is indices 0-3
    # byte_a should be at index 5
    # byte_b should be at index 6
    # byte_c should be at index 7
    print(f"Byte A (Function): {packed[5]:02x}")
    print(f"Byte B (Service):  {packed[6]:02x}")
    print(f"Byte C (Addtl):    {packed[7]:02x}")

if __name__ == "__main__":
    test_header_pack()
