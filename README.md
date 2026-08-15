# PRKit：簡報瑞士刀

[繁體中文](README.md) | [English](README.en.md)

跨平台的系統匣簡報輔助工具。程式不會開啟主視窗，所有設定都在系統匣圖示的右鍵選單中完成。

## 功能

- 聚光燈游標：可調整顏色、透明度與 48–320 px 圓圈大小；Windows 使用真正的系統游標，macOS/Linux 使用不攔截點擊的透明覆蓋層。
- 按鍵顯示：在游標所在螢幕中央下方顯示單鍵或組合鍵，不會攔截原本的鍵盤輸入。
- 自動保存：記住兩項功能的啟用狀態與外觀設定。
- 多螢幕與高 DPI：使用 Qt 邏輯像素定位與繪製。

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

若要固定特定版本，將 `latest` 改成版本標籤，例如 `v0.1.0`。

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
