import ctypes
from types import SimpleNamespace

import pytest

from prkit.mac_capslock import MacCapsLockState


def test_lock_reader_uses_capslock_selector_and_closes_once() -> None:
    locked = True
    closed = []

    def read(handle, selector, output):
        assert handle.value == 42
        assert selector == 1
        output._obj.value = locked
        return 0

    reader = object.__new__(MacCapsLockState)
    reader._handle = ctypes.c_uint32(42)
    reader._io = SimpleNamespace(
        IOHIDGetModifierLockState=read,
        IOServiceClose=lambda handle: closed.append(handle.value),
    )
    assert reader.read() is True
    locked = False
    assert reader.read() is False
    reader.close()
    reader.close()
    assert closed == [42]
    with pytest.raises(RuntimeError, match="已關閉"):
        reader.read()


def test_lock_read_failure_is_not_reported_as_off() -> None:
    reader = object.__new__(MacCapsLockState)
    reader._handle = ctypes.c_uint32(42)
    reader._io = SimpleNamespace(IOHIDGetModifierLockState=lambda *args: -1)
    with pytest.raises(RuntimeError, match="-1"):
        reader.read()
