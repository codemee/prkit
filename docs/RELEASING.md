# 雲端打包與發佈 / Cloud packaging and releases

桌面程式與 Python 套件都在 GitHub Actions 打包。本機只修改版本、文件與程式，執行品質檢查，再推送變更。

Desktop applications and Python distributions are built in GitHub Actions. Local work is limited to editing, versioning, and quality checks before pushing.

## 產物與流程 / Outputs and workflows

| Workflow | 觸發方式 / Trigger | 產物 / Output |
| --- | --- | --- |
| `ci.yml` / CI | Push、PR、手動 / manual | Windows、macOS、Linux 程式碼檢查與測試 / checks and tests |
| `desktop.yml` / Build desktop apps | `v*` 標籤、手動 / tags or manual | Windows x64 單檔 EXE、macOS Apple Silicon arm64 DMG、SHA-256 校驗檔 |
| `publish.yml` / Publish to PyPI | `v*` 標籤自動觸發；手動可重試 / tags or manual retry | Wheel、sdist，使用 PyPI Trusted Publishing 發佈 |

桌面版使用獨立 `build` 相依群組中的 PyInstaller，版本由 `uv.lock` 固定。Windows runner 為 `windows-latest`；macOS runner 為 `macos-15`（arm64）。不提供 Intel macOS 建置或 Linux 桌面安裝包。

Desktop builds use PyInstaller from the separate `build` dependency group, locked by `uv.lock`. Windows uses `windows-latest`; Apple Silicon uses `macos-15` (arm64). Intel macOS and Linux desktop packages are not built.

## 更新版本 / Prepare a version

1. 使用 `uv version <version>` 更新 `pyproject.toml` 與 `uv.lock`，並同步 `src/prkit/__init__.py` 的 `__version__`。
2. 更新 `CHANGELOG.md`、雙語 README 的版本範例與下載檔名；若行為或架構變更，也更新 `PRD.md` 與雙語技術設計。
3. 執行下列品質檢查，提交並推送到 `main`，等待 CI 通過。

Use `uv version <version>`, synchronize the runtime version in `src/prkit/__init__.py`, update release notes and affected documents, then run the checks below. Commit, push to `main`, and wait for CI.

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

## 雲端試打包 / Cloud trial build

```bash
gh workflow run desktop.yml --ref main
gh run list --workflow desktop.yml --limit 5
gh run view <run-id>
```

手動執行只上傳 Actions Artifacts，不建立 GitHub Release，也不發佈到 PyPI。兩個平台都成功後即可從執行頁下載測試包。

Manual runs upload Actions Artifacts only; they do not create a release or publish to PyPI. Both platform builds must succeed.

每次桌面建置都會：

1. 由專案 SVG 產生原生圖示，依 `desktop/PRKit.spec` 打包。
2. Windows 產生單一 EXE，內含 runtime 與 watchdog 模式；macOS 產生 `PRKit.app`，再建立含 Applications 捷徑的唯讀壓縮 DMG。
3. Windows 只將單一 EXE 複製到新暫存資料夾後執行 `--smoke-test`，確認不依賴旁置檔案；macOS 驗證並唯讀掛載 DMG，直接執行映像檔中的 App。測試包含 Qt/SVG、狀態提示與平台後端；Windows 驗證獨立 watchdog 就緒與正常退出，macOS 驗證 HID／輸入來源查詢、observer 清理與 App ad-hoc 簽章。
4. 成功後輸出 `.exe`／`.dmg` 與各自的 `.sha256`；測試報告另存為 `desktop-smoke-*` artifact。自動測試不會修改系統游標、授予輸入監控權限，也不取代使用者的桌面互動驗收。

Each cloud build generates icons and freezes the application. Windows copies only its single EXE to a new directory before testing, including an independently initialized watchdog and readiness handshake. macOS creates and verifies a compressed DMG with an Applications shortcut, mounts it read-only, and tests the app inside it. Tests check Qt/SVG, overlays, platform backends, and the macOS app signature. Successful builds produce EXE/DMG downloads and SHA-256 files, with separate smoke-test report artifacts. Tests do not change system cursors, grant Input Monitoring permission, or replace interactive acceptance tests.

## 發佈 / Publish

以下以 `0.2.1` 為例；版本標籤必須與套件及執行期版本一致。

Example for `0.2.1`; the version tag must match both package and runtime versions.

```bash
git tag v0.2.1
git push origin v0.2.1
```

推送標籤會自動觸發桌面打包。兩個平台都通過後，流程將 EXE、DMG 與校驗檔附到該版本的 GitHub Release；若不存在就建立草稿。草稿不會自動公開，讓維護者完成 PyPI 與版本說明後統一發布。

The tag automatically triggers both desktop builds and PyPI publishing. Once both desktop builds pass, the EXE, DMG, and checksums are attached to the matching GitHub Release, creating a draft if none exists. Drafts remain unpublished until the maintainer finishes PyPI verification and release notes.

推送同一版本標籤也會自動啟動 **Publish to PyPI**，無需另外按執行。下列手動指令僅供失敗後重試；同一 ref 的執行會排隊，`uv publish --check-url` 會檢查已存在的檔案以避免重複上傳。請先確認原執行結果，不要更改已發布的版本內容。

No separate dispatch is needed for PyPI. Use the manual command below only to retry a failed run. Runs for the same ref are serialized, and `uv publish --check-url` checks existing files to skip duplicate uploads. Inspect the original result first; never modify an already published version.

```bash
gh workflow run publish.yml --ref v0.2.1
gh run list --workflow publish.yml --limit 5
gh run view <run-id>
```

`publish.yml` 拒絕與版本不符的標籤或分支；其 build job 產生 wheel／sdist，publish job 使用 `pypi` environment 與 `id-token: write` 進行 Trusted Publishing，不需保存 PyPI API token。PyPI 必須預先信任 `codemee/prkit` 的 `publish.yml`／`pypi` environment。

`publish.yml` rejects branch refs and mismatched version tags, including manual runs. It builds wheel/sdist distributions and publishes with the `pypi` environment and OIDC (`id-token: write`). PyPI must already trust this repository, workflow, and environment; no API token is stored.

確認 PyPI 版本頁與桌面資產都存在後，將版本說明寫入檔案並公開 Release：

After verifying the PyPI version and all desktop assets, publish the draft with release notes from a file:

```bash
gh release edit v0.2.1 --title "prkit v0.2.1" --notes-file <release-notes.md> --draft=false --latest
git tag -f latest v0.2.1
git push origin refs/tags/latest --force
```

`latest` 是供 `uvx`／`uv tool install` 使用的可移動穩定版標籤；`v0.2.1` 等版本標籤保持不變。版本已存在 PyPI 時不可重傳同版，應先檢查遠端狀態；若需修改套件內容則建立新版本。

`latest` is the movable stable tag used by Git-based `uvx`/`uv tool install` commands. Version tags remain immutable. PyPI versions cannot be overwritten: inspect remote state before retrying, and use a new version for changed package contents.

## 簽署與下載 / Signing and downloads

目前 Windows 未以發行者憑證簽署，macOS 僅有 PyInstaller ad-hoc 簽章，尚未設定 Apple Developer ID／notarization。GitHub CI 的簽章檢查只確認 App bundle 完整性，不代表通過 Gatekeeper 公證。Windows 直接執行 EXE；macOS 開啟 DMG 並拖曳安裝 App。macOS 按鍵監看需由使用者授予 `PRKit` 輸入監控權限；輸入法狀態模式不需要。

Windows publisher signing and Apple Developer ID/notarization are not configured. The macOS ad-hoc signature verifies bundle integrity but is not Gatekeeper notarization. Run the Windows EXE directly; open the macOS DMG and drag the app into Applications. Users must grant `PRKit` Input Monitoring permission for keystroke monitoring; input source status needs no such permission.

實作依據 / References: [PyInstaller spec files](https://pyinstaller.org/en/stable/spec-files.html), [macOS packaging](https://pyinstaller.org/en/stable/feature-notes.html#macos-specific-options), [GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
