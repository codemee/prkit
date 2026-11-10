from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QLocale, QTranslator

ENGLISH = {
    "簡報瑞士刀": "PRKit",
    "選擇顏色": "Choose color",
    "啟用聚光燈游標": "Enable spotlight cursor",
    "聚光燈游標": "Spotlight cursor",
    "顏色": "Color",
    "透明度": "Opacity",
    "圓圈大小": "Circle size",
    "啟用按鍵顯示": "Enable keystroke display",
    "按鍵顯示": "Keystroke display",
    "Caps Lock／輸入法狀態": "Caps Lock / input source",
    "啟用狀態顯示": "Enable status display",
    " 秒": " sec",
    "一直顯示": "Always show",
    "狀態變化後的顯示時間；0 表示一直顯示": "Display time after a change; 0 means always show",
    "Caps Lock 指示燈": "Caps Lock indicator",
    "目前輸入法（中文／英文）": "Current input source (Chinese / English)",
    "顯示內容": "Display content",
    "背景顏色": "Background color",
    "顯示時間": "Display time",
    "顯示時可用滑鼠拖曳，位置會自動保存。": "Drag the indicator to move it. Its position is saved.",
    "⚠ Wayland 不保證支援全域按鍵與覆蓋層": "⚠ Wayland may not support global keys or overlays",
    "拖曳以移動狀態提示": "Drag to move the status indicator",
    "開機自動啟動": "Start at login",
    "語言": "Language",
    "隨系統": "System default",
    "中文": "Chinese",
    "英文": "English",
    "中文（注音）": "Chinese (Zhuyin)",
    "結束": "Quit",
    "確定": "OK",
    "無法設定開機自動啟動：{error}": "Could not change start at login: {error}",
    "無法顯示鍵盤狀態：{message}": "Could not display keyboard status: {message}",
    "無法啟用聚光燈游標：{error}": "Could not enable spotlight cursor: {error}",
    "無法更新聚光燈游標：{error}": "Could not update spotlight cursor: {error}",
    "無法啟用按鍵顯示：{error}": "Could not enable keystroke display: {error}",
    "未知錯誤": "Unknown error",
    "按鍵監聽已停止：{message}": "Keystroke monitoring stopped: {message}",
    "此桌面環境沒有可用的系統匣。": "No system tray is available in this desktop environment.",
    "PRKit 已在執行。": "PRKit is already running.",
    "無法檢查是否已有執行中的 PRKit：{error}": (
        "Could not check for a running PRKit instance: {error}"
    ),
}


def effective_language(preference: str) -> str:
    if preference == "system":
        if sys.platform == "darwin":
            from Foundation import NSLocale

            # Qt's locale can be C/English even when macOS prefers Chinese.
            languages = NSLocale.preferredLanguages()
        else:
            languages = QLocale.system().uiLanguages()
        for tag in languages:
            language = str(tag).replace("_", "-").split("-", 1)[0].lower()
            if language in {"zh", "en"}:
                return language
        return "en"
    return preference if preference in {"zh", "en"} else "zh"


def tr(text: str, language: str) -> str:
    return ENGLISH.get(text, text) if language == "en" else text


def set_qt_language(app: QCoreApplication, preference: str) -> None:
    """Translate Qt-owned dialogs alongside PRKit's own interface."""
    previous = getattr(app, "_prkit_qt_translator", None)
    if previous is not None:
        app.removeTranslator(previous)
        previous.deleteLater()
        app._prkit_qt_translator = None
    if effective_language(preference) != "zh":
        return

    path = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)) / "qtbase_zh_TW.qm"
    translator = QTranslator(app)
    if not translator.load(str(path)):
        raise RuntimeError(f"Could not load Qt translation: {path}")
    app.installTranslator(translator)
    app._prkit_qt_translator = translator
