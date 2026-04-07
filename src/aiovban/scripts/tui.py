import argparse
import asyncio
from typing import List, Optional

from textual import events, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, HorizontalScroll, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Label, RichLog, Static, Input, Button

from aiovban import VBANApplicationData, DeviceType
from aiovban.asyncio import AsyncVBANClient, VBANDevice
from aiovban.enums import Features, State, VBANBaudRate
from aiovban.packet import VBANPacket
from aiovban.packet.body import Utf8StringBody
from aiovban.packet.body.service.rt_packets import RTPacketBodyType0
from aiovban.packet.headers.service import ServiceType, VBANServiceHeader
from aiovban.packet.headers.text import VBANTextHeader, VBANTextStreamType

# --- Messages ---

class GainChanged(Message):
    def __init__(self, kind: str, index: int, value: float):
        self.kind = kind
        self.index = index
        self.value = value
        super().__init__()

class ToggleRequest(Message):
    def __init__(self, kind: str, index: int, target: str, current_state: bool):
        self.kind = kind
        self.index = index
        self.target = target
        self.current_state = current_state
        super().__init__()

class RenameRequested(Message):
    def __init__(self, kind: str, index: int, current_name: str):
        self.kind = kind
        self.index = index
        self.current_name = current_name
        super().__init__()

class MixerButtonPressed(Message):
    def __init__(self, button: "MixerButton"):
        self.button = button
        super().__init__()

# --- Rename Modal ---

class RenameModal(ModalScreen[str]):
    DEFAULT_CSS = """
    RenameModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #modal-container {
        width: 50;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    #modal-container Label {
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
        text-style: bold;
        color: white;
    }
    #modal-container Input {
        margin-bottom: 1;
    }
    #modal-container Horizontal {
        height: 3;
        align: center middle;
    }
    #modal-container Button {
        width: 1fr;
        margin: 0 1;
    }
    """
    def __init__(self, old_name: str):
        super().__init__()
        self.old_name = old_name

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-container"):
            yield Label("Rename Strip/Bus")
            yield Input(value=self.old_name, id="rename-input")
            with Horizontal():
                yield Button("Cancel", variant="error", id="cancel")
                yield Button("OK", variant="success", id="ok")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss(self.query_one(Input).value)
        else:
            self.dismiss(None)

    def on_mount(self) -> None:
        self.query_one(Input).focus()

# --- Custom Title Label ---

class TitleLabel(Label):
    def on_click(self) -> None:
        self.post_message(RenameRequested("enrich", 0, ""))

# --- Custom Button using Static ---

class MixerButton(Static):
    def __init__(self, label: str, id: Optional[str] = None, classes: str = ""):
        super().__init__(label, id=id, classes=classes)
        self.can_focus = True

    def on_click(self) -> None:
        self.post_message(MixerButtonPressed(self))

# --- VU Meter ---

def _level_bar(level: float, width: int = 16) -> str:
    filled = int(max(0.0, min(1.0, level)) * width)
    return "#" * filled + "-" * (width - filled)

class VUMeter(Static):
    levels: reactive[List[float]] = reactive([0.0, 0.0], layout=False)
    def render(self) -> str:
        lines = []
        for i, level in enumerate(self.levels[:2]):
            ch = "L" if i == 0 else "R"
            bar = _level_bar(level, width=18)
            color = "red" if level > 0.9 else "yellow" if level > 0.7 else "green"
            lines.append(f"{ch} [{color}]{bar}[/{color}]")
        return "\n".join(lines)

_BUS_FLAGS = [
    ("A1", State.MODE_BUSA1), ("A2", State.MODE_BUSA2), ("A3", State.MODE_BUSA3),
    ("B1", State.MODE_BUSB1), ("B2", State.MODE_BUSB2), ("B3", State.MODE_BUSB3),
]

# --- Strip Widget ---

class StripWidget(Vertical):
    DEFAULT_CSS = """
    StripWidget { width: 24; height: auto; border: solid white; background: black; padding: 0; margin: 0 1; }
    StripWidget Label { width: 100%; content-align: center middle; height: 1; color: white; }
    StripWidget TitleLabel { width: 100%; content-align: center middle; height: 1; background: white; color: black; text-style: bold; }
    StripWidget .gain-label { color: yellow; }
    StripWidget .gain-row { height: 1; layout: horizontal; margin: 1 0; }
    StripWidget .gain-bar { width: 10; color: cyan; }
    StripWidget .control-row { height: 1; layout: horizontal; margin: 1 0; }
    StripWidget .sub-header { color: #666; background: #111; }
    StripWidget .routing-container { height: auto; }
    StripWidget .btn-row { height: 1; layout: horizontal; }
    MixerButton { height: 1; content-align: center middle; background: #222; color: #ccc; margin: 0 1; width: 1fr; }
    MixerButton:hover { background: #444; color: white; }
    MixerButton.-active { background: #060; color: white; }
    MixerButton.-mute.-active { background: #600; color: white; }
    MixerButton.-solo.-active { background: #660; color: black; }
    MixerButton.-gain { width: 5; background: #333; }
    """

    def __init__(self, index: int, kind: str = "strip", **kwargs):
        super().__init__(**kwargs)
        self.index = index
        self.kind = kind
        self._default_label = f"{'STRIP' if kind == 'strip' else 'BUS'} {index + 1}"
        self._current_label = self._default_label
        self._name_label: TitleLabel = None
        self._vu: VUMeter = None
        self._mute_btn: MixerButton = None
        self._solo_btn: MixerButton = None
        self._bus_btns: dict = {}
        self._gain_label: Label = None
        self._gain_bar_label: Label = None
        self._current_gain = 0.0
        self._current_state = State(0)

    def compose(self) -> ComposeResult:
        self._name_label = TitleLabel(self._default_label)
        yield self._name_label
        self._vu = VUMeter()
        yield self._vu
        self._gain_label = Label("0.0 dB", classes="gain-label")
        yield self._gain_label
        with Horizontal(classes="gain-row"):
            yield MixerButton("-", id="gain-down", classes="-gain")
            self._gain_bar_label = Label("[----------]", classes="gain-bar")
            yield self._gain_bar_label
            yield MixerButton("+", id="gain-up", classes="-gain")
        with Horizontal(classes="control-row"):
            self._mute_btn = MixerButton("MUTE", id="mute", classes="-mute")
            yield self._mute_btn
            if self.kind == "strip":
                self._solo_btn = MixerButton("SOLO", id="solo", classes="-solo")
                yield self._solo_btn
        if self.kind == "strip":
            yield Label("ROUTING", classes="sub-header")
            with Vertical(classes="routing-container"):
                for i in range(0, len(_BUS_FLAGS), 3):
                    with Horizontal(classes="btn-row"):
                        for label, _ in _BUS_FLAGS[i : i + 3]:
                            btn = MixerButton(label, id=label.lower())
                            self._bus_btns[label] = btn
                            yield btn

    def on_rename_requested(self, event: RenameRequested) -> None:
        if event.kind == "enrich":
            event.stop()
            self.post_message(RenameRequested(self.kind, self.index, self._current_label))

    def on_mixer_button_pressed(self, event: MixerButtonPressed) -> None:
        event.stop()
        btn_id = event.button.id
        if btn_id == "gain-up":
            self.post_message(GainChanged(self.kind, self.index, min(12.0, self._current_gain + 1.0)))
        elif btn_id == "gain-down":
            self.post_message(GainChanged(self.kind, self.index, max(-60.0, self._current_gain - 1.0)))
        elif btn_id == "mute":
            self.post_message(ToggleRequest(self.kind, self.index, "Mute", bool(self._current_state & State.MODE_MUTE)))
        elif btn_id == "solo":
            self.post_message(ToggleRequest(self.kind, self.index, "Solo", bool(self._current_state & State.MODE_SOLO)))
        else:
            for label, flag in _BUS_FLAGS:
                if btn_id == label.lower():
                    self.post_message(ToggleRequest(self.kind, self.index, label, bool(self._current_state & flag)))
                    break

    def update(self, label: str, levels: List[float], state: State, gain: float) -> None:
        self._current_label = label or self._default_label
        self._name_label.update(self._current_label)
        self._vu.levels = levels[:2] if len(levels) >= 2 else levels + [0.0] * (2 - len(levels))
        self._current_state = state
        self._current_gain = gain
        self._mute_btn.set_class(bool(state & State.MODE_MUTE), "-active")
        pos = int(max(0, min(72, gain + 60)) / 72 * 10)
        self._gain_bar_label.update("[" + "=" * pos + "-" * (10 - pos) + "]")
        self._gain_label.update(f"{gain:.1f} dB")
        if self.kind == "strip" and self._solo_btn:
            self._solo_btn.set_class(bool(state & State.MODE_SOLO), "-active")
            for bus_label, flag in _BUS_FLAGS:
                if bus_label in self._bus_btns:
                    self._bus_btns[bus_label].set_class(bool(state & flag), "-active")

# --- App ---

class VBANTUIApp(App):
    CSS = """
    Screen { layout: vertical; background: black; }
    .section-header { background: #222; color: white; height: 1; content-align: center middle; }
    HorizontalScroll { height: 24; }
    #buses-scroll { height: 14; }
    #debug-log { height: 8; border: solid yellow; }
    #debug-log.-hidden { display: none; }
    """
    BINDINGS = [("q", "quit", "Quit"), ("d", "toggle_debug", "Debug")]
    TITLE = "VBAN TUI"

    def __init__(self, host: str, port: int, register: List[str], command_stream: str, **kwargs):
        super().__init__(**kwargs)
        self.vban_host = host
        self.vban_port = port
        self.register_targets = register
        self.command_stream_name = command_stream
        self._client: AsyncVBANClient = None
        self._devices: List[VBANDevice] = []
        self._cmd_framecount = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("--- INPUT STRIPS ---", classes="section-header")
        with HorizontalScroll(id="strips-scroll"):
            for i in range(8): yield StripWidget(i, kind="strip", classes="strip")
        yield Static("--- OUTPUT BUSES ---", classes="section-header")
        with HorizontalScroll(id="buses-scroll"):
            for i in range(8): yield StripWidget(i, kind="bus", classes="bus")
        yield RichLog(id="debug-log", classes="-hidden", max_lines=100, markup=True)
        yield Footer()

    async def on_mount(self) -> None:
        asyncio.create_task(self._run_vban())

    async def _run_vban(self) -> None:
        self._client = AsyncVBANClient(ignore_audio_streams=True, application_data=VBANApplicationData(application_name="VBAN TUI", features=Features.Audio | Features.Text, device_type=DeviceType.Receptor, version="0.1.0"))
        self._client.quick_reject = lambda addr: False
        _original = self._client.process_packet
        async def _hooked(address, port, packet: VBANPacket):
            if isinstance(packet.body, RTPacketBodyType0): self._on_rt_update(packet.body)
            await _original(address, port, packet)
        self._client.process_packet = _hooked
        await self._client.listen(self.vban_host, self.vban_port)
        self._debug(f"Listening on {self.vban_host}:{self.vban_port}")
        for target in self.register_targets:
            h, *p = target.split(":"); port = int(p[0]) if p else 6980
            device = await self._client.register_device(h, port)
            await device.rt_stream(update_interval=0xFF)
            self._devices.append(device)
            self._debug(f"Registered RT updates from {h}:{port}")
        while True: await asyncio.sleep(2)

    def action_toggle_debug(self) -> None: self.query_one("#debug-log", RichLog).toggle_class("-hidden")
    def _debug(self, msg: str) -> None: self.query_one("#debug-log", RichLog).write(msg)

    def _send_command(self, cmd: str) -> None:
        self._debug(f"PRE-SEND: {cmd}")
        if not self._devices:
            self._debug("ERROR: No devices registered")
            return
        device = self._devices[0]
        header = VBANTextHeader(baud=VBANBaudRate.RATE_256000, streamname=self.command_stream_name, stream_type=VBANTextStreamType.UTF_8)
        self._cmd_framecount += 1
        header.framecount = self._cmd_framecount
        packet = VBANPacket(header, Utf8StringBody(cmd))
        self._client.send_datagram(packet.pack(), (device.address, device.default_port))
        self._debug(f"DISPATCHED to {device.address}:{device.default_port}: {cmd}")

    def on_gain_changed(self, message: GainChanged) -> None:
        target = "Strip" if message.kind == "strip" else "Bus"
        self._send_command(f"{target}[{message.index}].Gain = {message.value:.1f};")

    def on_toggle_request(self, message: ToggleRequest) -> None:
        target = "Strip" if message.kind == "strip" else "Bus"
        self._send_command(f"{target}[{message.index}].{message.target} = {0 if message.current_state else 1};")

    @work
    async def on_rename_requested(self, message: RenameRequested) -> None:
        if message.kind == "enrich": return
        self._debug(f"Opening rename modal for {message.kind}[{message.index}]")
        new_name = await self.push_screen_wait(RenameModal(message.current_name))
        if new_name is not None:
            target = "Strip" if message.kind == "strip" else "Bus"
            cmd = f'{target}[{message.index}].Label = "{new_name}";'
            self._debug(f"Renaming to: {cmd}")
            self._send_command(cmd)

    def _on_rt_update(self, body: RTPacketBodyType0) -> None:
        self.sub_title = f"Raw packets: {self._client.raw_packets_received}"
        strips = self.query(StripWidget).filter(".strip")
        buses = self.query(StripWidget).filter(".bus")
        for i, strip in enumerate(body.strips):
            if i < len(strips):
                if i < 5: raw = body.input_levels[i * 2 : (i + 1) * 2]
                else: raw = body.input_levels[10 + (i - 5) * 8 : 10 + (i - 4) * 8]
                strips[i].update(strip.label, [v / 65535.0 for v in raw], strip.state, strip.layers[0] / 100.0)
        for i, bus in enumerate(body.buses):
            if i < len(buses):
                buses[i].update(bus.label, [v / 65535.0 for v in body.output_levels[i * 8 : (i + 1) * 8]], bus.state, bus.gain / 100.0)

    async def on_unmount(self) -> None:
        if self._client: self._client.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=6980)
    parser.add_argument("--command-stream", default="Command1")
    parser.add_argument("--register", nargs="+", default=[])
    args = parser.parse_args()
    VBANTUIApp(args.host, args.port, args.register, args.command_stream).run()

if __name__ == "__main__": main()
