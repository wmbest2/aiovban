import argparse
import asyncio
import time
from typing import List, Optional

from textual import events, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, HorizontalScroll, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Label, RichLog, Static, Input, Button

from aiovban import VBANApplicationData, DeviceType
from aiovban.asyncio import AsyncVBANClient, VBANDevice, VoicemeeterRemote
from aiovban.enums import Features, State, VBANBaudRate, VoicemeeterType
from aiovban.packet import VBANPacket
from aiovban.packet.body import Utf8StringBody
from aiovban.packet.body.service.rt_packets import RTPacketBodyType0
from aiovban.packet.headers.service import ServiceType, VBANServiceHeader
from aiovban.packet.headers.text import VBANTextHeader, VBANTextStreamType

# --- Theme Colors ---
COLOR_PHYS = "#0088AA"  # Cyan-Blue
COLOR_VIRT = "#8844AA"  # Amethyst Purple

# --- Messages ---

class GainChanged(Message):
    def __init__(self, kind: str, index: int, value: float):
        self.kind = kind; self.index = index; self.value = value
        super().__init__()

class ToggleRequest(Message):
    def __init__(self, kind: str, index: int, target: str, current_state: bool):
        self.kind = kind; self.index = index; self.target = target; self.current_state = current_state
        super().__init__()

class RenameRequested(Message):
    def __init__(self, kind: str, index: int, current_name: str):
        self.kind = kind; self.index = index; self.current_name = current_name
        super().__init__()

class MixerButtonPressed(Message):
    def __init__(self, button: "MixerButton"):
        self.button = button
        super().__init__()

# --- Separator ---

class VerticalSeparator(Static):
    DEFAULT_CSS = f"""
    VerticalSeparator {{
        width: 2; height: 100%; content-align: center middle;
        background: {COLOR_PHYS}; color: white; text-style: bold; margin: 0 1;
    }}
    VerticalSeparator.-virtual {{ background: {COLOR_VIRT}; }}
    VerticalSeparator.-hidden {{ display: none; }}
    """
    def __init__(self, label: str, id: str, classes: str = ""):
        super().__init__(id=id, classes=classes)
        self.label_text = label
    def render(self) -> str: return "\n".join(list(self.label_text))

# --- Rename Modal ---

class RenameModal(ModalScreen[str]):
    DEFAULT_CSS = """
    RenameModal { align: center middle; background: rgba(0, 0, 0, 0.8); }
    #modal-container { width: 50; height: auto; border: thick $primary; background: $surface; padding: 1 2; }
    #modal-container Label { width: 100%; content-align: center middle; margin-bottom: 1; text-style: bold; color: white; }
    #modal-container Input { margin-bottom: 1; }
    #modal-container Horizontal { height: 3; align: center middle; }
    #modal-container Button { width: 1fr; margin: 0 1; }
    """
    def __init__(self, old_name: str):
        super().__init__(); self.old_name = old_name
    def compose(self) -> ComposeResult:
        with Vertical(id="modal-container"):
            yield Label("Rename Strip/Bus"); yield Input(value=self.old_name, id="rename-input")
            with Horizontal(): yield Button("Cancel", variant="error", id="cancel"); yield Button("OK", variant="success", id="ok")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok": self.dismiss(self.query_one(Input).value)
        else: self.dismiss(None)
    def on_mount(self) -> None: self.query_one(Input).focus()

# --- Custom Title Label ---

class TitleLabel(Label):
    def on_click(self) -> None: self.post_message(RenameRequested("enrich", 0, ""))

# --- Custom Button using Static ---

class MixerButton(Static):
    def __init__(self, label: str, id: Optional[str] = None, classes: str = ""):
        super().__init__(label, id=id, classes=classes); self.can_focus = True
    def on_click(self) -> None: self.post_message(MixerButtonPressed(self))

# --- VU Meter ---

def _level_bar(level: float, width: int = 12) -> str:
    filled = int(max(0.0, min(1.0, level)) * width)
    return "#" * filled + "-" * (width - filled)

class VUMeter(Static):
    levels: reactive[List[float]] = reactive([0.0, 0.0], layout=False)
    def render(self) -> str:
        lines = []
        bar_width = 14 if len(self.levels) > 2 else 20
        for i, level in enumerate(self.levels):
            bar = _level_bar(level, width=bar_width)
            color = "red" if level > 0.9 else "yellow" if level > 0.7 else "green"
            lines.append(f"{i} [{color}]{bar}[/{color}]")
        return "\n".join(lines)

_BUS_FLAGS = [
    ("A1", State.MODE_BUSA1), ("A2", State.MODE_BUSA2), ("A3", State.MODE_BUSA3),
    ("B1", State.MODE_BUSB1), ("B2", State.MODE_BUSB2), ("B3", State.MODE_BUSB3),
]

# --- Strip Widget ---

class StripWidget(Vertical):
    DEFAULT_CSS = f"""
    StripWidget {{ width: 26; height: auto; border: solid {COLOR_PHYS}; background: $surface; padding: 0; margin: 0 1; }}
    StripWidget.-virtual {{ border: solid {COLOR_VIRT}; }}
    StripWidget Label {{ width: 100%; content-align: center middle; height: 1; color: $text; }}
    StripWidget TitleLabel {{ width: 100%; content-align: center middle; height: 1; background: {COLOR_PHYS}; color: white; text-style: bold; }}
    StripWidget.-virtual TitleLabel {{ background: {COLOR_VIRT}; color: white; }}
    StripWidget .gain-label {{ color: $accent; text-style: bold; }}
    StripWidget .gain-row {{ height: 1; layout: horizontal; margin: 1 0; }}
    StripWidget .gain-bar {{ width: 10; color: $secondary; }}
    StripWidget .control-row {{ height: 1; layout: horizontal; margin: 1 0; }}
    StripWidget .sub-header {{ color: $text-disabled; background: $panel; }}
    StripWidget .routing-container {{ height: auto; }}
    StripWidget .btn-row {{ height: 1; layout: horizontal; }}
    MixerButton {{ height: 1; content-align: center middle; background: $panel; color: $text-muted; margin: 0 1; width: 1fr; }}
    MixerButton:hover {{ background: $primary-darken-1; color: white; }}
    MixerButton.-active {{ background: $success; color: white; }}
    MixerButton.-mute.-active {{ background: #600; color: white; }}
    MixerButton.-solo.-active {{ background: #660; color: black; }}
    MixerButton.-gain {{ width: 5; background: $panel-lighten-1; }}
    """

    def __init__(self, index: int, kind: str = "strip", **kwargs):
        super().__init__(**kwargs)
        self.index = index; self.kind = kind
        self._default_label = f"{'STRIP' if kind == 'strip' else 'BUS'} {index + 1}"
        self._current_label = self._default_label
        self._name_label: TitleLabel = None; self._vu: VUMeter = None; self._mute_btn: MixerButton = None
        self._solo_btn: MixerButton = None; self._bus_btns: dict = {}; self._gain_label: Label = None
        self._gain_bar_label: Label = None; self._current_gain = 0.0; self._current_state = State(0)

    def compose(self) -> ComposeResult:
        self._name_label = TitleLabel(self._default_label); yield self._name_label
        self._vu = VUMeter(); yield self._vu
        self._gain_label = Label("0.0 dB", classes="gain-label"); yield self._gain_label
        with Horizontal(classes="gain-row"):
            yield MixerButton("-", id="gain-down", classes="-gain")
            self._gain_bar_label = Label("[----------]", classes="gain-bar"); yield self._gain_bar_label
            yield MixerButton("+", id="gain-up", classes="-gain")
        with Horizontal(classes="control-row"):
            self._mute_btn = MixerButton("MUTE", id="mute", classes="-mute"); yield self._mute_btn
            if self.kind == "strip":
                self._solo_btn = MixerButton("SOLO", id="solo", classes="-solo"); yield self._solo_btn
        if self.kind == "strip":
            yield Label("ROUTING", classes="sub-header")
            with Vertical(classes="routing-container"):
                for i in range(0, len(_BUS_FLAGS), 3):
                    with Horizontal(classes="btn-row"):
                        for label, _ in _BUS_FLAGS[i : i + 3]:
                            btn = MixerButton(label, id=label.lower()); self._bus_btns[label] = btn; yield btn

    def on_rename_requested(self, event: RenameRequested) -> None:
        if event.kind == "enrich":
            event.stop(); self.post_message(RenameRequested(self.kind, self.index, self._current_label))

    def on_mixer_button_pressed(self, event: MixerButtonPressed) -> None:
        event.stop(); btn_id = event.button.id
        if btn_id == "gain-up": self.post_message(GainChanged(self.kind, self.index, min(12.0, self._current_gain + 1.0)))
        elif btn_id == "gain-down": self.post_message(GainChanged(self.kind, self.index, max(-60.0, self._current_gain - 1.0)))
        elif btn_id == "mute": self.post_message(ToggleRequest(self.kind, self.index, "Mute", bool(self._current_state & State.MODE_MUTE)))
        elif btn_id == "solo": self.post_message(ToggleRequest(self.kind, self.index, "Solo", bool(self._current_state & State.MODE_SOLO)))
        else:
            for label, flag in _BUS_FLAGS:
                if btn_id == label.lower():
                    self.post_message(ToggleRequest(self.kind, self.index, label, bool(self._current_state & flag))); break

    def update(self, label: str, levels: List[float], state: State, gain: float, is_virtual: bool = False) -> None:
        self._current_label = label or self._default_label; self._name_label.update(self._current_label)
        self._vu.levels = levels; self._current_state = state; self._current_gain = gain
        self.set_class(is_virtual, "-virtual"); self._mute_btn.set_class(bool(state & State.MODE_MUTE), "-active")
        pos = int(max(0, min(72, gain + 60)) / 72 * 10); self._gain_bar_label.update("[" + "=" * pos + "-" * (10 - pos) + "]")
        self._gain_label.update(f"{gain:.1f} dB")
        if self.kind == "strip" and self._solo_btn:
            self._solo_btn.set_class(bool(state & State.MODE_SOLO), "-active")
            for bus_label, flag in _BUS_FLAGS:
                if bus_label in self._bus_btns: self._bus_btns[bus_label].set_class(bool(state & flag), "-active")

# --- App ---

class VBANTUIApp(App):
    CSS = """
    Screen { layout: vertical; background: $background; }
    .section-header { background: #111; color: $text-muted; height: 1; content-align: center middle; border-bottom: solid #333; }
    .global-bar { height: 3; background: $panel; border-bottom: solid #444; align: center middle; }
    .global-btn { width: 24; background: #333; color: white; height: 1; content-align: center middle; margin: 0 2; }
    .global-btn:hover { background: $primary; }
    HorizontalScroll { height: 32; }
    #buses-scroll { height: 18; }
    #debug-log { height: 8; border: solid yellow; }
    #debug-log.-hidden { display: none; }
    """
    BINDINGS = [("q", "quit", "Quit"), ("d", "toggle_debug", "Debug")]
    TITLE = "VBAN TUI"

    def __init__(self, host: str, port: int, register: List[str], command_stream: str, **kwargs):
        super().__init__(**kwargs)
        self.vban_host = host; self.vban_port = port; self.register_targets = register
        self.command_stream_name = command_stream; self._client: AsyncVBANClient = None
        self._remote: Optional[VoicemeeterRemote] = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="global-bar"):
            yield MixerButton("RESTART AUDIO ENGINE", id="global-restart", classes="global-btn")
            yield MixerButton("SHOW VM WINDOW", id="global-show", classes="global-btn")
        yield Static("--- INPUT STRIPS ---", classes="section-header")
        with HorizontalScroll(id="strips-scroll"):
            yield VerticalSeparator("PHYS", id="sep-strip-phys")
            for i in range(8):
                if i == 2: yield VerticalSeparator("VIRT", id="sep-strip-2", classes="-hidden -virtual")
                if i == 3: yield VerticalSeparator("VIRT", id="sep-strip-3", classes="-hidden -virtual")
                if i == 5: yield VerticalSeparator("VIRT", id="sep-strip-5", classes="-hidden -virtual")
                yield StripWidget(i, kind="strip", classes="strip")
        yield Static("--- OUTPUT BUSES ---", classes="section-header")
        with HorizontalScroll(id="buses-scroll"):
            yield VerticalSeparator("PHYS", id="sep-bus-phys")
            for i in range(8):
                if i == 2: yield VerticalSeparator("VIRT", id="sep-bus-2", classes="-hidden -virtual")
                if i == 3: yield VerticalSeparator("VIRT", id="sep-bus-3", classes="-hidden -virtual")
                if i == 5: yield VerticalSeparator("VIRT", id="sep-bus-5", classes="-hidden -virtual")
                yield StripWidget(i, kind="bus", classes="bus")
        yield RichLog(id="debug-log", classes="-hidden", max_lines=100, markup=True); yield Footer()

    async def on_mount(self) -> None:
        self.set_interval(1.0, self._update_status)
        asyncio.create_task(self._run_vban())

    def _update_status(self) -> None:
        if not self._remote:
            self.sub_title = "INITIALIZING..."
            return
        status = "[ONLINE]" if self._remote.online else "[OFFLINE]"
        if self._remote.type: self.sub_title = f"{self._remote.type.name} {self._remote.version} {status}"
        else: self.sub_title = f"VBAN DEVICE {status}"

    async def _run_vban(self) -> None:
        self._client = AsyncVBANClient(ignore_audio_streams=True, application_data=VBANApplicationData(application_name="VBAN TUI", features=Features.Audio | Features.Text, device_type=DeviceType.Receptor, version="0.1.0"))
        self._client.quick_reject = lambda addr: False
        
        # We NO LONGER hook process_packet here because we use the Remote's callback
        await self._client.listen(self.vban_host, self.vban_port)
        for target in self.register_targets:
            h, *p = target.split(":"); port = int(p[0]) if p else 6980
            device = await self._client.register_device(h, port)
            self._remote = VoicemeeterRemote(device, self.command_stream_name)
            self._remote.add_callback(self._on_remote_update)
            await self._remote.start()
        while True: await asyncio.sleep(2)

    def _on_remote_update(self, remote: VoicemeeterRemote) -> None:
        """Callback from VoicemeeterRemote when new state arrives."""
        # This is called frequently, so we just trigger a UI update
        # In Textual, we can call self.refresh() or just let the update logic handle it
        # Actually, we need the original body to get VU levels, or we update remote to store levels too
        pass

    def on_mixer_button_pressed(self, event: MixerButtonPressed) -> None:
        if event.button.id == "global-restart" and self._remote: asyncio.create_task(self._remote.restart())
        elif event.button.id == "global-show" and self._remote: asyncio.create_task(self._remote.show())

    def on_gain_changed(self, message: GainChanged) -> None:
        if self._remote: asyncio.create_task(self._remote.strips[message.index].set_gain(message.value) if message.kind == "strip" else self._remote.buses[message.index].set_gain(message.value))

    def on_toggle_request(self, message: ToggleRequest) -> None:
        if not self._remote: return
        obj = self._remote.strips[message.index] if message.kind == "strip" else self._remote.buses[message.index]
        nv = not message.current_state
        if message.target == "Mute": asyncio.create_task(obj.set_mute(nv))
        elif message.target == "Solo": asyncio.create_task(obj.set_solo(nv))
        else: asyncio.create_task(obj.set_bus_routing(message.target, nv))

    @work
    async def on_rename_requested(self, message: RenameRequested) -> None:
        if message.kind != "enrich" and self._remote:
            new_name = await self.push_screen_wait(RenameModal(message.current_name))
            if new_name is not None: await (self._remote.strips[message.index] if message.kind == "strip" else self._remote.buses[message.index]).set_label(new_name)

    def _on_rt_update(self, body: RTPacketBodyType0) -> None:
        # We still need the raw body here because the TUI shows VU levels which aren't yet in the Remote abstraction
        if self._remote: self._remote.apply_rt_packet(body)
        
        st_widgets = self.query(StripWidget).filter(".strip")
        bus_widgets = self.query(StripWidget).filter(".bus")
        v_type = body.voice_meeter_type
        
        phys_in = 2 if v_type == VoicemeeterType.VOICEMEETER else 3 if v_type == VoicemeeterType.BANANA else 5
        phys_out = 2 if v_type == VoicemeeterType.VOICEMEETER else 3 if v_type == VoicemeeterType.BANANA else 5
        
        for k, v in [("strip", phys_in), ("bus", phys_out)]:
            for idx in [2, 3, 5]:
                q = self.query(f"#sep-{k}-{idx}")
                if q: q.first().set_class(idx != v, "-hidden")

        active_strips = self._remote.strips
        for i, w in enumerate(st_widgets):
            is_active = i < len(active_strips)
            w.set_class(not is_active, "-hidden")
            if is_active:
                s = active_strips[i]
                if i < phys_in: raw = body.input_levels[i*2:(i+1)*2]
                else: raw = body.input_levels[10+(i-phys_in)*8:10+(i-phys_in+1)*8]
                w.update(s.label, [v/65535.0 for v in raw], body.strips[i].state, s.gain, s.is_virtual)

        active_buses = self._remote.buses
        for i, w in enumerate(bus_widgets):
            is_active = i < len(active_buses)
            w.set_class(not is_active, "-hidden")
            if is_active:
                b = active_buses[i]
                w.update(b.label, [v/65535.0 for v in body.output_levels[i*8:(i+1)*8]], body.buses[i].state, b.gain, b.is_virtual)

    async def on_unmount(self) -> None:
        if self._remote: await self._remote.stop()
        if self._client: self._client.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0"); parser.add_argument("--port", type=int, default=6980)
    parser.add_argument("--command-stream", default="Command1"); parser.add_argument("--register", nargs="+", default=[])
    args = parser.parse_args(); VBANTUIApp(args.host, args.port, args.register, args.command_stream).run()

if __name__ == "__main__": main()
