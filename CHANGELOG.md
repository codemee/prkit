# Changelog / 版本紀錄

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
