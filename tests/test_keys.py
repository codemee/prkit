from dataclasses import dataclass

from prkit.keys import KeyChordTracker, key_label


@dataclass(frozen=True)
class FakeKey:
    name: str | None = None
    char: str | None = None
    vk: int | None = None


def test_formats_special_and_character_keys() -> None:
    assert key_label(FakeKey(name="enter")) == "Enter"
    assert key_label(FakeKey(char="a", vk=65)) == "A"
    assert key_label(FakeKey(char=" ", vk=32)) == "Space"


def test_chord_orders_modifiers_and_ignores_repeat() -> None:
    tracker = KeyChordTracker()
    ctrl = FakeKey(name="ctrl_l")
    shift = FakeKey(name="shift_r")
    letter = FakeKey(char="p", vk=80)

    assert tracker.press(letter) == "P"
    assert tracker.press(ctrl) == "Ctrl + P"
    assert tracker.press(shift) == "Ctrl + Shift + P"
    assert tracker.press(letter) is None


def test_release_reports_only_when_every_key_is_up() -> None:
    tracker = KeyChordTracker()
    ctrl = FakeKey(name="ctrl_l")
    letter = FakeKey(char="c", vk=67)
    tracker.press(ctrl)
    tracker.press(letter)

    assert not tracker.release(letter)
    assert tracker.label == "Ctrl"
    assert tracker.release(ctrl)
    assert tracker.label == ""


def test_left_and_right_modifiers_have_distinct_state() -> None:
    tracker = KeyChordTracker()
    left = FakeKey(name="ctrl_l")
    right = FakeKey(name="ctrl_r")
    tracker.press(left)
    tracker.press(right)

    assert tracker.label == "Ctrl"
    assert not tracker.release(left)
    assert tracker.release(right)
