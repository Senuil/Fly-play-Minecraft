# FlyCraft：果蠅 connectome → Minecraft 玩家 prototype

已實作且測通 **真實 FlyWire v783 小型連線探針 → LIF 神經模擬 → Mineflayer 玩家移動／轉向**。
完整資料也已成功匯入與執行 CPU 基準測試。

**範圍很重要：預設真實探針只有 6 個神經元、6 條聚合連線，感測與動作對應為人工指定。**
它驗證真實神經連線可以放進遊戲控制閉環，並不代表果蠅已理解 Minecraft，
也不是已辨認的果蠅視覺／運動迴路。完整全腦即時控制、GPU 加速、天然導航迴路尚未完成。
`--demo` 則是另附的人工電路，不能當作 connectome 成果。

## 快速開始：Windows PowerShell

使用 Python 3.12 與 Node.js 22 以上（本次測試 Node 24）。解壓後進入專案根目錄。
以下直接呼叫 venv 的 Python，不需要修改 PowerShell execution policy。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-tested.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
npm --prefix bridge ci
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
npm --prefix bridge test
```

不需要自行架伺服器，就能重跑本地網路整合測試：

```powershell
.\.venv\Scripts\python.exe scripts/test_minecraft.py
```

這會啟動暫時的 Flying Squid 伺服器（Minecraft 1.16.5 協定）、真實探針神經服務與正式 bot 入口，
在平地旁放置障礙，驗證伺服器收到位移及轉向封包後結束。不含 Mojang 伺服器下載。
此測試不是 Paper 1.21.9 驗證；Windows 本機也仍須由你執行一次。

Linux/macOS 可用 `python3 -m venv .venv`，其後把 Windows Python 路徑換成 `.venv/bin/python`。

## 讓它加入你的 Minecraft 世界

第一階段使用**獨立的 Mineflayer 玩家帳號**，不會接管目前開著的真人客戶端。
以 Java Edition、平地、低模組負載的私人測試世界開始。
大量 Fabric/Forge 模組所需的自訂握手與內容未支援；不要先用 600 模組伺服器測。

終端 A（專案根目錄）：

```powershell
.\.venv\Scripts\python.exe -m flycraft.server --bundle fixtures/probe --mapping fixtures/probe/mapping.json
```

終端 B（專案根目錄）：

```powershell
$env:MC_HOST="127.0.0.1"
$env:MC_PORT="25565"
$env:MC_VERSION="1.21.9"
$env:MC_AUTH="offline"
$env:MC_USERNAME="FlyConnectome"
npm --prefix bridge start
```

上述 offline 範例只適用於你自己已有的私人離線測試伺服器；不會修改伺服器設定。
正版驗證伺服器改成 `MC_AUTH="microsoft"` 與 bot 使用的 Microsoft 帳號，
依 Mineflayer 顯示的裝置登入流程完成驗證。真人與 bot 同時遊玩應使用不同帳號。
LAN 世界請把 `MC_PORT` 換成遊戲顯示的實際埠號。

Minecraft 版本可透過 `MC_VERSION` 調整；本版依賴固定為 Mineflayer 4.39.0。
1.21.9 是預設目標；實際網路整合僅驗證 1.16.5。

按 Ctrl+C 停止。神經服務逾時（300 ms）、失效指令、死亡或斷線會清除操作。
獨立 watchdog 在最後一次有效操作超過 350 ms 後停止前進。
視線前方過近的實體方塊會觸發額外安全停止；這是工程保護，並非神經決策。
尚無落差／岩漿避險、採礦、戰鬥或尋路能力。

## 架構與訊號

| 模組 | 輸入／輸出與責任 |
|---|---|
| `bridge/control.mjs` | Minecraft 方塊幾何 → 左右障礙接近度 0–1；前方停止檢查 |
| `bridge/index.mjs` | 每個 physicsTick 最多一個 HTTP 請求；序號、逾時、操作執行 |
| `flycraft/server.py` | 只綁定 127.0.0.1；單 bot session；限制請求大小與數值 |
| `flycraft/controller.py` | 接近度 → 0–180 Hz 刺激；輸出群放電率 → 前進與角速度 |
| `flycraft/model.py` | 持久神經狀態、CSR 稀疏連線、延遲、LIF 與不應期 |
| `flycraft/import_shiu.py` | 上游 Parquet/CSV → 權重 NPZ、字串 root IDs、來源雜湊 |
| `fixtures/probe/` | 真實 v783 六神經元誘導子圖；可直接啟動，不需下載全腦 |
| `tests/`、`bridge/*test*` | 因果消融、輸入驗證、資料精度、跨語言 HTTP 測試 |
| `docs/` | 研究比較、模型假設、測試範圍、下一階段 |

輸入包含固定的 `drive=1`（人工持續驅動），以及左右各 45°、最遠 4 格的方塊接近度。
這是遊戲幾何感測，尚非複眼影像。左側障礙刺激送入一群神經元，
另一群的放電率解碼為右轉；此對應是工程配置，不是生物註解。
輸出群與輸入群禁止重疊，避免直接用被刺激神經元冒充傳播結果。

每次請求前進 50 ms 神經時間，內部步長 0.1 ms。跨請求保留膜電位、突觸狀態與延遲。
遊戲與神經時間在慢運算時會分離；沒有累積待辦佇列，也不追補落後的 ticks。
前進閾值為平滑後 5 Hz；角速度 `(左轉率－右轉率)/40`，上限 ±1.5 rad/s。
本版只控制前進與 yaw，不跳躍、不衝刺、不操作物品。

## 完整資料、子圖與基準測試

下載約 104 MB 的兩個上游檔案，並檢查本次取得資料的 SHA-256：

```powershell
.\.venv\Scripts\python.exe scripts/download_data.py
.\.venv\Scripts\python.exe -m flycraft.import_shiu --completeness data/Completeness_783.csv --connectivity data/Connectivity_783.parquet --output data/full
.\.venv\Scripts\python.exe -m flycraft.benchmark --bundle data/full --mapping fixtures/probe/mapping.json --steps 3
```

完整匯入得到 **138,639 neurons / 15,091,983 聚合 edges**。
這是 Shiu 釋出模型檔案的實際數量，不能與 FlyWire 整體的 139,255 neurons、
突觸接點數、或其他閾值下的 edge 數混為一談。
基準使用同一組人工 probe 刺激與讀出 ID，但保留完整網路。
全腦目前只適合離線 benchmark，**不要把這個 CPU 基線視為可即時控制的配置**。

重建隨附的探針：

```powershell
.\.venv\Scripts\python.exe -m flycraft.import_shiu --completeness data/Completeness_783.csv --connectivity data/Connectivity_783.parquet --output data/probe-rebuilt --probe
```

`--probe` 從資料挑選三對強興奮性連線，彼此沒有跨對連線，保留所選六個神經元間的所有邊。
選擇規則是用來測試訊號路徑；不能由此推論天然行為。
自選子圖使用 `--ids your-ids.json`（字串 ID 陣列），並按 `config/mapping.template.json` 配置輸入輸出。
匯入會保留上游帶符號權重，將多重連線加總，不猜測神經傳遞物質的正負號。
此匯入器只支援 Shiu 這組欄位，不能直接拿任意 Codex CSV 或 Zenodo Feather 代入。

## 你的新筆電

32 GB RAM、兩顆 1 TB SSD、RTX 5070 適合開始這個原型。小型探針不需要 GPU。
完整 CSR 權重本次佔 **121,290,424 bytes（約 116 MiB）**；此數字不含匯入表格、神經狀態、
Python 與 Minecraft 的記憶體。14 萬平方的 dense float32 矩陣則約 78 GB，禁止轉 dense。

目前 Linux CPU 的小探針每 50 ms 神經時間約花 10–15 ms；全腦約花 11 秒。
這不是你的筆電測值，也不能直接估算 5070 的加速倍數。
GPU 後端尚未實作。請先執行以下指令確認 GPU 顯存與 driver，而不是從「5070」猜規格：

```powershell
.\.venv\Scripts\python.exe scripts/hardware_info.py
.\.venv\Scripts\python.exe -m flycraft.benchmark --bundle fixtures/probe --mapping fixtures/probe/mapping.json --steps 100
```

硬體、工具取捨與官方來源見 [docs/research.md](docs/research.md)；後續見 [docs/roadmap.md](docs/roadmap.md)。

## GitHub 狀態

專案位置：[Senuil/Fly-play-Minecraft](https://github.com/Senuil/Fly-play-Minecraft)。
第一版放在 `main` 分支，保留程式、lockfile、六神經元 fixture、來源與測試文件。
大型原始資料與依賴目錄不入 Git，使用下載／安裝指令重建。

可以在專案頁面按綠色 **Code → Download ZIP** 下載，解壓縮後依上面的
Windows 步驟執行。GitHub 是存放程式與追蹤版本的地方；上傳程式不會自動接管你的 Minecraft。
後續更新可用分支與 Pull Request 留下修改記錄。

來源與授權見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
