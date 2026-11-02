import sys
from types import SimpleNamespace

from prkit import autostart


def test_windows_login_entry_can_be_enabled_and_removed(monkeypatch) -> None:
    entries = {}

    class Key:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    def query(_key, name):
        if name not in entries:
            raise FileNotFoundError(name)
        return entries[name], 1

    def delete(_key, name):
        if name not in entries:
            raise FileNotFoundError(name)
        del entries[name]

    fake = SimpleNamespace(
        HKEY_CURRENT_USER=1,
        REG_SZ=1,
        OpenKey=lambda *_args: Key(),
        CreateKey=lambda *_args: Key(),
        QueryValueEx=query,
        SetValueEx=lambda _key, name, _reserved, _kind, value: entries.update({name: value}),
        DeleteValue=delete,
    )
    monkeypatch.setitem(sys.modules, "winreg", fake)
    monkeypatch.setattr(autostart.sys, "platform", "win32")
    monkeypatch.setattr(autostart, "launch_command", lambda: [r"C:\Program Files\PRKit.exe"])

    assert not autostart.is_enabled()
    autostart.set_enabled(True)
    assert autostart.is_enabled()
    assert entries["PRKit"] == '"C:\\Program Files\\PRKit.exe"'
    autostart.set_enabled(False)
    assert not autostart.is_enabled()
