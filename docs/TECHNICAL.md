# 技術設計

[繁體中文](TECHNICAL.md) | [English](TECHNICAL.en.md)

本文說明簡報瑞士刀的跨平台後端、macOS 原生整合及相關安全邊界。

## 元件與資料流

`AppController` 負責讀寫設定並協調系統匣、聚光燈、鍵盤監看與提示覆蓋層。系統匣面板關閉後才啟動鍵盤後端，避免在 macOS 原生選單追蹤迴圈內初始化事件監看器。鍵盤後端只送出格式化前的按下／放開事件；`KeyChordTracker` 去除重複事件並維護目前按鍵集合，`KeystrokeOverlay` 顯示最後一次完整組合，在所有按鍵放開後延遲淡出。

主程式在建立系統匣前，以 Qt `QLockFile` 鎖住目前使用者的本機應用程式資料目錄；所有安裝位置共用鎖路徑。重複啟動會提示已有實例並結束，權限或 I/O 錯誤則顯示錯誤且不繼續。鎖隨主程式生命週期釋放，意外退出後由 Qt 辨識並清除過期鎖；游標 watchdog 與打包 smoke test 不進入主程式入口，因此不取得這把鎖。

Qt 應用程式全域視窗圖示使用與系統匣相同的 PRKit SVG；所有啟動提示交談窗再明確指定此圖示作為標題列圖示。提示使用精簡的自訂 `QDialog`，以 20 px 狀態標記、置中對齊的文字及扁平按鈕取代預設的大型訊息圖示。交談窗依字寬計算尺寸並固定寬高，長訊息在限定寬度內換行，避免視窗被意外放大。系統匣警告通知也傳入 PRKit 圖示，讓訊息來源一致。

## macOS 聚光燈與覆蓋層

macOS 沒有支援背景程式跨應用程式替換系統游標的公開 API，因此聚光燈使用透明 Qt 工具視窗跟隨 `QCursor`。Cocoa 原生視窗另套用以下限制：

- `NSFloatingWindowLevel`：高於一般應用程式，低於選單列與彈出選單。
- `NSWindowStyleMaskNonactivatingPanel` 與 `WA_ShowWithoutActivating`：顯示時不成為 key window。
- `hidesOnDeactivate = false`：切換應用程式後仍維持顯示。
- 關閉陰影、邊框及不透明背景，並忽略所有滑鼠事件。
- 加入所有 Space，且可顯示於全螢幕輔助空間。

系統匣面板展開前會同步一次游標位置，避免原生選單追蹤期間 Qt 計時器暫停而留下舊位置。

## macOS 鍵盤監看

macOS 使用 Core Graphics `CGEventTapCreate`，位置為 `kCGHIDEventTap`／`kCGHeadInsertEventTap`，選項固定為 `kCGEventTapOptionListenOnly`。選擇 HID 前端是為了在 Carbon 全域快捷鍵或其他快捷鍵工具處理事件前取得副本；listen-only 保證 callback 的回傳值不能用來阻止事件繼續傳遞。

事件 tap 在專用 Core Foundation run loop 執行。callback 不操作 Qt widget 或 Qt timer，只透過 Qt signal 將資料排回主執行緒。監看範圍限於 `keyDown`、`keyUp` 與 `flagsChanged`：

- 修飾鍵狀態從事件 flags 重建，避免遺失或重複事件造成黏鍵。
- 左右修飾鍵合併為 Command、Shift、Option、Control 的顯示狀態。
- `keycode 255` 是系統狀態事件，會直接忽略。
- Caps Lock 以一次性按鍵顯示，不會因鎖定狀態永久留在組合中。
- ANSI 字母、數字、方向鍵與常用標點使用實體 keycode 映射，不記錄輸入文字。

此後端需要 macOS「輸入監控」權限。程式只在記憶體中維護當前按鍵狀態，不保存、記錄或傳送按鍵內容。

## 其他平台

- Windows 聚光燈替換真正的系統游標，並由獨立 watchdog 在異常終止後復原；鍵盤監看使用 `pynput`。
- Linux 聚光燈使用透明覆蓋層，鍵盤監看使用 `pynput`。X11 支援較完整；Wayland 受全域輸入與點擊穿透協定限制。

## Caps Lock 與輸入法狀態

`AppController` 依 `CapsLockSettings.mode` 啟動其中一個狀態監看器，共用可拖曳的 `CapsLockOverlay`。切換模式時先停止兩個監看器並隱藏舊提示，再啟動選中的來源；已停止模式的狀態訊號不會覆蓋目前文字。此功能與按鍵顯示分開啟用。

| 平台 | Caps Lock 狀態來源 | 輸入法模式 |
| --- | --- | --- |
| Windows | `GetKeyState(0x14)` 的 toggle bit | 未實作，不顯示選項 |
| macOS | IOKit `IOHIDGetModifierLockState` | 支援目前選中的系統輸入來源 |
| Linux X11 | 根視窗 `query_pointer()` 的 `LockMask` | 未實作，不顯示選項 |
| Wayland | 不支援，啟用失敗後還原開關並通知 | 不支援 |

### macOS Caps Lock 指示燈模式

`MacCapsLockState` 透過 `ctypes` 連接 `IOHIDSystem`，以 `kIOHIDCapsLockState` 查詢系統鎖定狀態。這是系統鎖定值，不是對鍵盤 LED 的直接讀值。`CapsLockMonitor` 每 100 毫秒查詢一次；若已具備輸入監控權限，另啟動 listen-only 鍵盤監看器，在 `flagsChanged` 時透過 Qt signal 喚醒主執行緒重新查詢。權限不足時維持輪詢，事件 flags 本身永遠不直接決定 ON／OFF。停止時會關閉 HID 連線與事件監看器。

macOS 若啟用 Caps Lock 切換中英文，短按可能產生短暫 ON 後回到 OFF；長按才啟用持續大寫鎖定。輸入法切換與大寫鎖定是不同狀態，程式不會自行反轉或鎖住 ON 來模擬英文輸入模式。

### macOS 輸入法模式

`MacInputSourceReader` 透過 HIToolbox 的 `TISCopyCurrentKeyboardInputSource` 及 `TISGetInputSourceProperty` 取得輸入來源 ID 與本地化名稱，每次查詢都以 `CFRelease` 釋放取得的來源參照。`InputSourceMonitor` 訂閱 `kTISNotifySelectedKeyboardInputSourceChanged` 的分散式通知，並以 100 毫秒輪詢補足通知；只有來源變更才更新提示。

- 內建注音 `com.apple.inputmethod.TCIM.Zhuyin` 顯示「中文（注音）」。
- ABC／美式鍵盤顯示「英文」，其他輸入來源顯示其本地化名稱。
- 追蹤的是系統選中的輸入來源，不推測第三方輸入法在同一來源內的私有中英文模式。
- 此模式不使用鍵盤事件 tap，不需要輸入監控權限，也不讀取輸入文字。
- 原生通知 block 必須回傳 `None`，不能直接回傳 `Signal.emit()` 的結果；否則 PyObjC 會在收到通知時拋出例外並終止程式。
- 停止時移除原生通知 observer；讀取失敗會停止監看、還原啟用開關並通知使用者。

### 顯示與設定保存

覆蓋層在 Qt 主執行緒更新，以 `repaint()` 立即繪製狀態；macOS 關閉原生視窗動畫，且只在缺少 nonactivating 樣式時設定，避免反覆重設樣式。不使用強制啟用視窗或 `orderFrontRegardless()`。

Caps Lock 提示顯示 ON／OFF，輸入法模式顯示來源名稱；調整外觀時保留目前文字。顯示時間為 1–60 秒，0 表示持續顯示；拖曳時暫停倒數，放開後保存位置並重新計時。模式、啟用狀態、顏色、透明度、時間與位置使用 `QSettings` 的 `capslock/*` 鍵保存。舊設定預設使用 `capslock` 模式；未知模式與非 macOS 平台回復 Caps Lock 模式。

## 開機啟動與語言

`autostart.py` 以目前使用者的登入機制管理開機啟動：Windows 使用 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 的 `PRKit` 值；macOS 寫入 `~/Library/LaunchAgents/com.codemee.prkit.plist`；Linux 寫入 XDG 設定目錄下的 `autostart/prkit.desktop`。停用時只移除 PRKit 自己的項目。系統匣選單每次打開時重新讀取實際狀態；寫入失敗會還原核取方塊並顯示錯誤。打包版使用目前 EXE／App 的執行檔路徑，Python 安裝版使用同環境的 Python 執行 `-m prkit`（Windows 優先使用 `pythonw.exe`）。

語言偏好保存在 `QSettings` 的 `language` 鍵，值為 `system`、`zh` 或 `en`。`system` 在 macOS 讀取 `NSLocale.preferredLanguages()`，其他平台讀取 `QLocale.system().uiLanguages()`，依偏好順序選取第一個支援的中文或英文；皆不支援時使用英文。三態按鈕切換後即時更新系統匣選單與提示文字。Qt 的應用程式名稱維持固定，避免語言切換改變既有設定的儲存位置。

色塊與語言按鈕採無框線、圓角與 hover 背景，區段使用平面分隔線。macOS 原生選單的內嵌控制項不提供滑鼠追蹤，因此點擊系統匣圖示時改以 `QMenu.popup()` 顯示 Qt 選單；選單開啟期間以 40 ms 計時器檢查游標是否位於語言按鈕內，透過 `pointerHover` 屬性更新背景，關閉選單即停止並清除 hover。其他平台保留系統匣的 context menu。

Qt 內建的色彩選擇視窗使用 `qtbase_zh_TW.qm` 翻譯；啟動及切換語言時安裝或移除 `QTranslator`，讓色票區、欄位與操作按鈕跟隨所選語系。色彩預覽按鈕的樣式表只匹配自身的 `colorSwatch` 名稱，不影響其子視窗的操作按鈕配色。桌面打包測試會驗證 Qt 翻譯檔可載入。

## 桌面打包

`desktop/PRKit.spec` 使用 PyInstaller 將 Python、Qt 與平台相依套件一起打包：Windows 使用 onedir 資料夾並以 ZIP 散布，避免每次啟動都解壓；macOS 使用 App bundle，設定固定 bundle ID `com.codemee.prkit`、版本與 `LSUIElement`，維持僅選單列顯示的行為，並以 `CFBundleLocalizations` 宣告英文、繁體中文與簡體中文。圖示由既有 SVG 在雲端轉成 ICO／ICNS；macOS App 使用 ad-hoc 簽章，經 `ditto` 複製後，以 `hdiutil` 建立包含 App 與 Applications 捷徑的壓縮唯讀 DMG。

Windows EXE 以 `--cursor-watchdog` 模式啟動另一個獨立程序；入口在載入 Qt 前先分流，因此不會開啟第二個 GUI。子程序保留 `PYINSTALLER_RESET_ENVIRONMENT=1`，確保它能在主程式異常退出後獨立運作；資料夾版共用磁碟上的 `_internal`，不會再次解壓。父程序等待就緒事件（最多 30 秒），確認 watchdog 已開啟父程序／停止事件控制代碼後，才允許啟用聚光燈。啟動時若聚光燈設定為啟用，這段等待在背景執行，Qt 主執行緒可先處理系統匣；使用者期間取消啟用或結束時會停止多餘的 watchdog。停止時通知並等待 watchdog 退出；初始化失敗會清理控制代碼。從 Python 安裝時仍支援同環境的 console-script helper 或 `python -m prkit.cursor_watchdog`。PyInstaller 明確收集 `pynput` 的動態 Windows 後端。

`desktop/build.py` 只由 Windows／macOS runner 執行。Windows 將完整資料夾打成 ZIP，再解壓到新暫存資料夾，確認 `PRKit.exe` 與 `_internal` 存在；macOS 驗證、唯讀掛載 DMG 並確認 Applications 捷徑，再執行其中 App 的 `--smoke-test`。測試報告寫入檔案，適用沒有 stdout 的 GUI 執行檔；測試不載入使用者偏好、不啟用聚光燈、不修改游標。Windows 實際驗證 watchdog 就緒與正常退出；macOS 驗證 HID、輸入來源查詢與 observer 清理，並檢查映像檔內 App 的簽章。成功後才輸出校驗檔及上傳套件。

`desktop.yml` 於版本標籤或手動觸發，在 GitHub 建置 Windows x64 與 macOS arm64；版本標籤建置完成後將資產附到 Release，必要時建立草稿。`publish.yml` 同樣在推送 `v*` 標籤後自動建置並發佈 PyPI，保留手動重試，並驗證版本標籤與套件版本一致；相同 ref 排隊執行，上傳前檢查已存在的檔案。完整流程見[發佈指南](RELEASING.md)。

## 驗證

提交前執行：

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

macOS 手動驗證應涵蓋游標進入選單列、展開系統匣面板、切換焦點、中英文輸入、一般字母與標點、修飾組合鍵，以及已被其他快捷鍵工具註冊的組合。

狀態提示另須驗證：短按 Caps Lock 切換注音／ABC、長按啟用大寫鎖定、透過選單或快捷鍵切換輸入來源、不移動滑鼠時仍更新、切換顯示模式、修改外觀後文字不變、拖曳與重啟後位置還原。自動測試涵蓋狀態來源不被事件 flags 覆蓋、通知回呼回傳值、來源變更與去重、失敗清理、模式切換與設定保存。

版本與發佈程序見[發佈指南](RELEASING.md)，使用者可見變更見[版本紀錄](../CHANGELOG.md)。
