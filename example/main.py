import asyncio

from asyncvban.asyncio import AsyncVBANClient
from asyncvban.enums import VBANBaudRate
from asyncvban.packet import VBANPacket
from asyncvban.packet.body.service import RTPacketBodyType0, Ping, DeviceType, Features
from asyncvban.packet.headers.service import VBANServiceHeader, ServiceType, PingFunctions
from asyncvban.packet.headers.text import VBANTextHeader


async def main():
    client = AsyncVBANClient('bill.local', 6980, queue_size=10)
    await client.connect()


    txt_header = VBANTextHeader(baud=VBANBaudRate.RATE_256000, framecount=1)
    txt_packet = VBANPacket(header=txt_header, body=bytes(";", 'utf-8'))
    print(txt_packet)
    await client.send_packet(txt_packet)

    # Create a VBAN packet
    header = VBANServiceHeader(service=ServiceType.RTPacketRegister)
    packet = VBANPacket(header=header)

    # Send the packet
    await client.send_packet(packet)

    # Receive a packet

    async def loop_with_timeout():
        while True:
            received_packet = await client.receive_packet()

            if type(received_packet.header) == VBANServiceHeader:
                await handle_service_message(received_packet)
            else:
                print(received_packet)


    async def handle_service_message(received_packet):
        if received_packet.header.service == ServiceType.RTPacket:
            print(RTPacketBodyType0.unpack(received_packet.body))
        elif received_packet.header.service == ServiceType.Identification:
            ping_header = VBANServiceHeader(function=PingFunctions.Response, service=ServiceType.Identification,
                                            additional_info=0x0)
            print(Ping.unpack(received_packet.body))

            ping = Ping(DeviceType.Receptor, Features.Text | Features.Audio | Features.Serial, 0, "FF0000", "1.0.0.0",
                        applicationName="Bills cool app")
            await client.send_packet(VBANPacket(header=ping_header, body=ping.pack()))
        elif received_packet.header.service == ServiceType.Chat_UTF8:
            print(received_packet.body.decode('utf-8'))

    try:
        await asyncio.wait_for(loop_with_timeout(), timeout=100.0)
    except asyncio.TimeoutError:
        print("The operation timed out")

    await client.close()

asyncio.run(main())