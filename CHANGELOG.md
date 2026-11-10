# Changelog / 版本紀錄

## [0.3.4] - 2026-11-10

- 色彩預覽按鈕的樣式只套用在色塊本身，色彩視窗內的操作按鈕維持系統配色，避免深色選值使文字難以辨識。
- 色彩視窗的內建色票、欄位與按鈕會跟隨「隨系統／中文／英文」語言設定；桌面打包測試也會驗證繁體中文翻譯檔。
- Scope the selected-color style to the swatch so color-picker action buttons retain readable system colors.
- Translate Qt's built-in color picker with the selected system, Chinese, or English language; verify the translation in desktop bundles.

## [0.3.3] - 2026-11-10

- 修正 macOS 繁體中文系統在「隨系統」模式下顯示英文；改讀系統偏好語言，並在 App 宣告支援的語言。
- 色塊與語言按鈕改為無框線、圓角的扁平樣式，分隔線改為平面細線。
- macOS 改用 Qt 彈出選單，並在選單開啟時追蹤游標位置，修正語言按鈕沒有 hover 背景的問題。
- Fix English appearing in system language mode on Traditional Chinese macOS by reading preferred UI languages and declaring supported app localizations.
- Use flat, borderless color and language buttons with rounded corners and flat section dividers.
- Use a Qt popup on macOS and track the pointer while it is open so the language button reliably shows its hover background.

## [0.3.2] - 2026-11-09

- 同一使用者只能執行一份 PRKit；重複啟動會顯示提示並結束，意外退出後可重新啟動。
- 啟動提示與系統匣通知使用 PRKit 應用程式圖示；提示改為雙語、精簡的扁平交談窗。
- 提示視窗依訊息內容固定大小，長訊息會換行，避免視窗意外放大。
- Allow only one PRKit GUI instance per user; a second launch shows a message and exits, while stale locks are recovered after a crash.
- Use the PRKit icon for startup dialogs and tray notifications, and replace the default message box with a compact bilingual dialog.
- Size startup dialogs to their content, wrapping long messages and preventing accidental enlargement.

## [0.3.1] - 2026-11-08

- Windows 桌面版改用資料夾打包 ZIP，避免每次啟動解壓單檔 EXE；打包測試會從解壓後的資料夾執行。
- 已保存的聚光燈設定在背景等待游標 watchdog 就緒，避免啟動時阻塞系統匣。
- 明確以 GPL-3.0-or-later 授權，並在 Python 套件與桌面下載檔附上授權全文。
- Package Windows as a folder ZIP to avoid unpacking a one-file EXE on every launch, and test the extracted bundle.
- Wait for the saved spotlight's cursor watchdog in the background so the tray remains responsive during startup.
- Declare GPL-3.0-or-later and include its full text in Python distributions and desktop downloads.

## [0.3.0] - 2026-11-02

### 新增 / Added

- 系統匣選單新增目前使用者的開機自動啟動核取方塊；Windows 使用登錄檔，macOS 使用 LaunchAgent，Linux 使用 XDG autostart。
- 新增地球／「中」／「En」三態語言按鈕，可即時切換隨系統、中文與英文，並保存選擇。
- Add a start-at-login checkbox backed by the per-user Windows Run key, macOS LaunchAgent, or Linux XDG autostart entry.
- Add an instant, persistent three-state language button for system default, Chinese, and English.

### 發佈 / Publishing

- PyPI 在推送 `v*` 版本標籤後自動發布，保留手動重試；相同 ref 排隊執行，並在上傳前檢查已存在的檔案。
- Automatically publish to PyPI on `v*` tag pushes, retaining serialized manual retries and duplicate-file checks.

## [0.2.1] - 2026-10-15

### 變更 / Changed

- Windows x64 改為單一 `.exe`，直接下載執行，不需另外解壓執行環境或 watchdog。
- 單檔 EXE 以專用參數啟動獨立 watchdog，使用獨立解壓環境與就緒握手，保留主程式異常終止後的游標復原能力。
- macOS Apple Silicon 改為 `.dmg`，包含 `PRKit.app` 與 Applications 捷徑，供拖曳安裝。
- GitHub 雲端建置會驗證獨立 EXE，以及唯讀掛載 DMG 內的 App，並提供 SHA-256 校驗檔。
- Windows x64 is distributed as a standalone EXE with an independent watchdog mode and startup handshake.
- Apple Silicon macOS is distributed as a DMG with an Applications shortcut. Cloud tests verify the standalone EXE and the app inside the mounted DMG.

## [0.2.0] - 2026-10-15

### 新增

- 可拖曳的 Caps Lock ON／OFF 提示，支援 Windows、macOS 與 Linux X11。
- 可設定背景顏色、透明度、顯示時間（含持續顯示），並保存位置與設定。
- macOS 可選擇顯示目前輸入法：內建注音顯示「中文（注音）」，ABC／美式鍵盤顯示「英文」。其他來源顯示其名稱，無需輸入監控權限。
- GitHub 雲端自動打包 Windows x64 執行檔與 macOS Apple Silicon App，附解壓成品測試、SHA-256 校驗檔與 Release 資產上傳。

### 修正

- macOS Caps Lock 改讀 IOKit 系統鎖定狀態，避免事件 flags 與輪詢互相覆蓋。
- 狀態提示立即重繪，停用 macOS 原生視窗動畫，避免反覆套用相同視窗樣式。
- 修正原生輸入來源通知回呼回傳非 `None`，導致切換輸入法時程式崩潰的問題。

### 平台範圍

- Windows／Linux X11 僅提供 Caps Lock 模式；輸入法模式目前僅支援 macOS。
- macOS 的中英文來源切換與大寫鎖定分開追蹤；不推測第三方輸入法來源內部的私有模式。
- Wayland 不支援狀態偵測。桌面版以 ZIP 提供 Windows 執行檔資料夾與 Apple Silicon `.app`，另保留 PyPI 套件；未提供 Intel macOS 版、`.dmg` 或 Windows 安裝精靈。
- 桌面版尚未設定 Windows 發行者簽章或 Apple Developer ID／公證；macOS 使用 ad-hoc 簽章。

### English

- Add a draggable Caps Lock indicator for Windows, macOS, and Linux X11 with saved appearance, duration, and position settings.
- Add a macOS-only input source mode that follows Zhuyin, ABC/U.S., and other selected system sources without Input Monitoring permission.
- Read macOS lock state through IOKit, keep event flags from overriding it, and repaint the indicator immediately.
- Disable native overlay animations and avoid reapplying an unchanged window style.
- Fix a PyObjC notification callback return value that could crash the application when switching input sources.
- Add GitHub cloud builds for Windows x64 and Apple Silicon macOS, testing extracted bundles and attaching ZIPs/checksums to releases.
- Windows/Linux input source mode, private modes within third-party input methods, Wayland status monitoring, Intel macOS builds, DMG/setup installers, and publisher signing/notarization are not included.

Earlier releases are listed on [GitHub Releases](https://github.com/codemee/prkit/releases).

[0.2.0]: https://github.com/codemee/prkit/compare/v0.1.1...v0.2.0
[0.2.1]: https://github.com/codemee/prkit/compare/v0.2.0...v0.2.1
[0.3.4]: https://github.com/codemee/prkit/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/codemee/prkit/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/codemee/prkit/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/codemee/prkit/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/codemee/prkit/compare/v0.2.1...v0.3.0
