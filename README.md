# PRKit：簡報瑞士刀

[繁體中文](README.md) | [English](README.en.md)

跨平台的系統匣簡報輔助工具。程式不會開啟主視窗，所有設定都在系統匣圖示的右鍵選單中完成。

## 功能

- 聚光燈游標：可調整顏色、透明度與 48–320 px 圓圈大小；Windows 使用真正的系統游標，macOS/Linux 使用不攔截點擊的透明覆蓋層。
- 按鍵顯示：在游標所在螢幕中央下方顯示單鍵或組合鍵，不會攔截原本的鍵盤輸入。
- Caps Lock 狀態：以可拖曳的小圓角矩形顯示 ON／OFF，可設定顯示時間、背景顏色與透明度。
- macOS 輸入法狀態：可切換為顯示目前的中文／英文輸入來源，與 Caps Lock 燈號分開追蹤。
- 自動保存：記住各項功能的啟用狀態、外觀設定與 Caps Lock 提示位置。
- 多螢幕與高 DPI：使用 Qt 邏輯像素定位與繪製。

## 下載桌面版

從 [GitHub Releases](https://github.com/codemee/prkit/releases/latest) 下載，不需另外安裝 Python 或 uv：

| 平台 | 下載檔案 | 啟動方式 |
| --- | --- | --- |
| Windows x64 | `PRKit-0.2.0-windows-x64.zip` | 完整解壓後執行 `PRKit/PRKit.exe` |
| macOS Apple Silicon | `PRKit-0.2.0-macos-arm64.zip` | 解壓後將 `PRKit.app` 移到「應用程式」再開啟 |

Windows 須保留同資料夾的 `prkit-cursor-watchdog.exe` 與 `_internal`，不可只複製主程式。macOS 目前僅提供 Apple Silicon 版。程式啟動後顯示在系統匣／選單列，不會開啟主視窗。

桌面版尚未使用 Windows 發行者憑證或 Apple Developer ID 簽署／公證；macOS 僅使用 ad-hoc 簽章。若系統阻擋你確認來源的下載檔案，請依系統安全提示允許開啟。macOS 按鍵顯示仍需在「輸入監控」允許 `PRKit`；輸入法狀態模式不需此權限。每個 ZIP 另提供 `.sha256` 校驗檔。

版本標籤會自動觸發 GitHub 雲端打包與成品測試；手動建置可在 Actions 的 **Build desktop apps** 執行，成品在該次執行的 Artifacts。詳細操作見[發佈指南](docs/RELEASING.md)。

## 從 PyPI 安裝

需要先安裝 [uv](https://docs.astral.sh/uv/)，再執行：

```powershell
uv tool install prkit
prkit
```

也可以從已下載的專案目錄安裝：

```powershell
uv tool install .
prkit
```

或直接從 GitHub 安裝最新正式版；`latest` 標籤會在每次正式發布時更新：

```powershell
uv tool install git+https://github.com/codemee/prkit.git@latest
prkit
```

若要固定特定版本，將 `latest` 改成版本標籤，例如 `v0.2.0`。

若安裝後找不到 `prkit` 指令，執行 `uv tool update-shell`，再重新開啟終端機。移除工具可使用 `uv tool uninstall prkit`。

## 使用 uvx 免安裝執行

直接從 PyPI 執行：

```powershell
uvx prkit
```

也可以在已下載的專案目錄執行，或直接從 GitHub 執行最新正式版：

```powershell
uvx --from . prkit
uvx --from git+https://github.com/codemee/prkit.git@latest prkit
```

`uvx` 會在隔離環境中準備並執行程式，不會把 `prkit` 持久安裝到工具目錄。

## Caps Lock／輸入法狀態顯示

啟動後，右鍵點擊系統匣圖示，在「Caps Lock／輸入法狀態」勾選「啟用狀態顯示」。此功能可獨立於按鍵顯示使用，啟用時會先顯示目前狀態。

macOS 可在「顯示內容」選擇「Caps Lock 指示燈」或「目前輸入法（中文／英文）」。輸入法模式直接追蹤系統選中的輸入來源：內建注音顯示「中文（注音）」，ABC／美式鍵盤顯示「英文」，其他輸入來源顯示其名稱；使用 Caps Lock、快捷鍵或選單切換都會更新。此模式不需要輸入監控權限，也不會把切換中英文時短暫出現的 Caps Lock 狀態當成大寫鎖定。

- **顯示時間**：設定狀態變化後顯示 1–60 秒；設為 0（「一直顯示」）便會持續顯示目前狀態。
- **背景顏色與透明度**：透過色塊與滑桿調整，修改時會顯示預覽。
- **移動位置**：直接用滑鼠左鍵拖曳提示框；拖曳期間暫停隱藏倒數，放開後重新計時並保存位置。下次啟動沿用，若原螢幕已移除則回到可見螢幕。

| 平台 | Caps Lock ON／OFF | 目前輸入法 |
| --- | --- | --- |
| Windows | 支援 | 未支援，不顯示選項 |
| macOS | 支援 | 支援 |
| Linux X11 | 支援 | 未支援，不顯示選項 |
| Wayland | 未支援 | 未支援 |

macOS 啟用 Caps Lock 切換輸入方式時，短按切換中英文，按住直到大寫鎖定符號出現才啟用持續大寫。若要跟隨中英文，請選擇輸入法模式；Caps Lock 模式顯示系統鎖定狀態。輸入法模式不推測第三方輸入法在同一來源內的私有中英文狀態。Wayland 啟用時會提示並自動停用。

## 開發

Python 3.12、虛擬環境及相依套件均由 uv 管理：

```powershell
uv sync
uv run prkit
```

品質檢查：

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

## 平台注意事項

- Windows：不需要額外權限。啟用聚光燈時會暫時替換系統游標，停用或結束時自動恢復；隨工具一併安裝的獨立 watchdog 會在主程式異常終止時復原游標。
- macOS：按鍵顯示使用 HID 層的唯讀事件監看，需要在「系統設定 → 隱私權與安全性 → 輸入監控」允許啟動本程式的應用程式（例如 ChatGPT、Terminal 或其他啟動 `prkit` 的終端程式）。監看器不會修改或攔截事件；即使組合鍵被其他快捷鍵工具處理，仍可先顯示按鍵。
- Linux：完整支援目標為 X11，桌面環境必須提供 StatusNotifierItem 或 XEmbed 系統匣。GNOME 可能需要 AppIndicator 類型的擴充套件。
- Wayland：受全域輸入與覆蓋層協定限制，按鍵顯示和點擊穿透不保證可用；程式會在選單中顯示警告。

按鍵內容只用於即時畫面顯示，不會寫入設定、檔案或日誌。

實作架構、macOS 原生視窗層級、權限模型與鍵盤事件流程請參閱[技術設計](docs/TECHNICAL.md)。

各版本變更見[版本紀錄](CHANGELOG.md)，雲端打包與 PyPI 發佈程序見[發佈指南](docs/RELEASING.md)。
