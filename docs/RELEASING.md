# 雲端打包與發佈 / Cloud packaging and releases

桌面程式與 Python 套件都在 GitHub Actions 打包。本機只修改版本、文件與程式，執行品質檢查，再推送變更。

Desktop applications and Python distributions are built in GitHub Actions. Local work is limited to editing, versioning, and quality checks before pushing.

## 產物與流程 / Outputs and workflows

| Workflow | 觸發方式 / Trigger | 產物 / Output |
| --- | --- | --- |
| `ci.yml` / CI | Push、PR、手動 / manual | Windows、macOS、Linux 程式碼檢查與測試 / checks and tests |
| `desktop.yml` / Build desktop apps | `v*` 標籤、手動 / tags or manual | Windows x64 ZIP、macOS Apple Silicon arm64 App ZIP、SHA-256 校驗檔 |
| `publish.yml` / Publish to PyPI | 手動，指定版本標籤 / manual on a version tag | Wheel、sdist，使用 PyPI Trusted Publishing 發佈 |

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
2. Windows 將 `PRKit.exe`、獨立 watchdog 與共用執行環境放入同一資料夾；macOS 產生 `PRKit.app`。
3. 壓縮後在暫存資料夾重新解壓，執行成品的 `--smoke-test`，驗證 Qt/SVG、狀態提示與平台後端。Windows 實際啟動及正常停止 watchdog，不修改系統游標；macOS 查詢 HID 與輸入來源，驗證通知訂閱、清理與 ad-hoc 簽章。
4. 成功後輸出 ZIP 與 `.zip.sha256`；測試報告另存為 `desktop-smoke-*` artifact。自動測試不會授予輸入監控權限，也不取代使用者的桌面互動驗收。

Each build generates native icons, freezes the application, archives it, then tests a freshly extracted copy. The smoke test checks Qt/SVG, overlays, and platform backends. Windows starts and normally stops the bundled watchdog without changing cursors. macOS checks HID/input source queries, observer lifecycle, and the ad-hoc signature. Successful builds produce ZIPs and SHA-256 files, with separate smoke-test report artifacts. Automated checks do not grant Input Monitoring permission or replace interactive desktop acceptance tests.

## 發佈 / Publish

以下以 `0.2.0` 為例；版本標籤必須與套件及執行期版本一致。

Example for `0.2.0`; the version tag must match both package and runtime versions.

```bash
git tag v0.2.0
git push origin v0.2.0
```

推送標籤會自動觸發桌面打包。兩個平台都通過後，流程將 ZIP 與校驗檔附到該版本的 GitHub Release；若不存在就建立草稿。草稿不會自動公開，讓維護者完成 PyPI 與版本說明後統一發布。

The tag triggers desktop builds automatically. Once both pass, archives and checksums are attached to the matching GitHub Release, creating a draft if none exists. Drafts remain unpublished until the maintainer finishes PyPI verification and release notes.

```bash
gh workflow run publish.yml --ref v0.2.0
gh run list --workflow publish.yml --limit 5
gh run view <run-id>
```

`publish.yml` 拒絕與版本不符的標籤或分支；其 build job 產生 wheel／sdist，publish job 使用 `pypi` environment 與 `id-token: write` 進行 Trusted Publishing，不需保存 PyPI API token。PyPI 必須預先信任 `codemee/prkit` 的 `publish.yml`／`pypi` environment。

`publish.yml` rejects branch refs and mismatched version tags. It builds wheel/sdist distributions and publishes with the `pypi` environment and OIDC (`id-token: write`). PyPI must already trust this repository, workflow, and environment; no API token is stored.

確認 PyPI 版本頁與桌面資產都存在後，將版本說明寫入檔案並公開 Release：

After verifying the PyPI version and all desktop assets, publish the draft with release notes from a file:

```bash
gh release edit v0.2.0 --title "prkit v0.2.0" --notes-file <release-notes.md> --draft=false --latest
git tag -f latest v0.2.0
git push origin refs/tags/latest --force
```

`latest` 是供 `uvx`／`uv tool install` 使用的可移動穩定版標籤；`v0.2.0` 等版本標籤保持不變。版本已存在 PyPI 時不可重傳同版，應先檢查遠端狀態；若需修改套件內容則建立新版本。

`latest` is the movable stable tag used by Git-based `uvx`/`uv tool install` commands. Version tags remain immutable. PyPI versions cannot be overwritten: inspect remote state before retrying, and use a new version for changed package contents.

## 簽署與下載 / Signing and downloads

目前 Windows 未以發行者憑證簽署，macOS 僅有 PyInstaller ad-hoc 簽章，尚未設定 Apple Developer ID／notarization。GitHub CI 的簽章檢查只確認 App bundle 完整性，不代表通過 Gatekeeper 公證。Windows ZIP 必須完整解壓並保留 watchdog 與 `_internal`。macOS 按鍵監看需由使用者授予 `PRKit` 輸入監控權限；輸入法狀態模式不需要。

Windows publisher signing and Apple Developer ID/notarization are not configured. The macOS ad-hoc signature verifies bundle integrity but is not Gatekeeper notarization. Keep the complete Windows directory, including the watchdog and `_internal`. Users must grant `PRKit` Input Monitoring permission for keystroke monitoring; input source status needs no such permission.

實作依據 / References: [PyInstaller spec files](https://pyinstaller.org/en/stable/spec-files.html), [macOS packaging](https://pyinstaller.org/en/stable/feature-notes.html#macos-specific-options), [GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
