import pytest

from prkit.input_source import InputSource, InputSourceMonitor, MacInputSourceReader


@pytest.mark.parametrize(
    ("identifier", "name", "label"),
    [
        ("com.apple.inputmethod.TCIM.Zhuyin", "Zhuyin", "中文（注音）"),
        ("com.apple.keylayout.ABC", "ABC", "英文"),
        ("com.apple.keylayout.US", "U.S.", "英文"),
        ("com.apple.keylayout.French", "French", "French"),
    ],
)
def test_input_source_label(identifier, name, label) -> None:
    assert InputSource(identifier, name).label == label


def test_source_changes_without_keyboard_events(qtbot, monkeypatch) -> None:
    import prkit.input_source as module

    current = InputSource("com.apple.inputmethod.TCIM.Zhuyin", "Zhuyin")
    closed = []
    callbacks = []

    class Reader:
        def observe(self, callback):
            callbacks.append(callback)

        def read(self):
            return current

        def close(self):
            closed.append(True)

    monkeypatch.setattr(module.sys, "platform", "darwin")
    monkeypatch.setattr(module, "MacInputSourceReader", Reader)
    monitor = InputSourceMonitor()
    states = []
    monitor.changed.connect(states.append)
    try:
        monitor.start()
        assert states == ["中文（注音）"]
        current = InputSource("com.apple.keylayout.ABC", "ABC")
        qtbot.waitUntil(lambda: states == ["中文（注音）", "英文"])
        callbacks[0]()
        assert states == ["中文（注音）", "英文"]
        current = InputSource("com.apple.inputmethod.TCIM.Zhuyin", "Zhuyin")
        callbacks[0]()
        assert states == ["中文（注音）", "英文", "中文（注音）"]
    finally:
        monitor.stop()
    callbacks[0]()
    assert closed == [True]
    assert not monitor._timer.isActive()


def test_source_read_failure_stops_monitor(qapp, monkeypatch) -> None:
    import prkit.input_source as module

    closed = []

    class Reader:
        def observe(self, callback):
            pass

        def read(self):
            raise RuntimeError("no input source")

        def close(self):
            closed.append(True)

    monkeypatch.setattr(module.sys, "platform", "darwin")
    monkeypatch.setattr(module, "MacInputSourceReader", Reader)
    monitor = InputSourceMonitor()
    errors = []
    monitor.failed.connect(errors.append)
    monitor.start()
    assert errors == ["no input source"]
    assert closed == [True]
    assert monitor._reader is None
    assert not monitor._timer.isActive()


def test_native_notification_callback_discards_refresh_return_value(monkeypatch) -> None:
    import ctypes
    import sys
    from types import SimpleNamespace

    callbacks = []
    refreshed = []

    class Center:
        def addObserverForName_object_queue_usingBlock_(self, name, sender, queue, callback):
            callbacks.append(callback)
            return object()

    monkeypatch.setitem(
        sys.modules,
        "AppKit",
        SimpleNamespace(
            NSDistributedNotificationCenter=SimpleNamespace(defaultCenter=lambda: Center())
        ),
    )
    monkeypatch.setattr(
        ctypes, "c_void_p", SimpleNamespace(in_dll=lambda *args: SimpleNamespace(value=1))
    )
    reader = object.__new__(MacInputSourceReader)
    reader._tis = object()
    reader._string = lambda value: "test.notification"

    def refresh():
        refreshed.append(True)
        return True

    reader.observe(refresh)
    assert callbacks[0](None) is None
    assert refreshed == [True]
