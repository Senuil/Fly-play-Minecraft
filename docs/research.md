# 資料與模擬工具評估

查閱與實作日期：2026-09-11 UTC。以下是本次工程選擇，不宣稱涵蓋所有最新專案。

## 資料選擇

| 資料 | 內容與取得方式 | 本專案判斷 |
|---|---|---|
| FlyWire FAFB v783 | 成人雌果蠅腦，官方整體 139,255 神經元；Codex 可瀏覽與下載、Zenodo 有 bulk 資料 | 主要資料系統；有既有全腦 LIF 模型可對照 |
| Shiu 模型 v783 匯出 | GitHub 的 `Completeness_783.csv`、`Connectivity_783.parquet`，包含索引與帶符號連線權重 | 本次實際下載與匯入的版本；138,639 神經元、15,091,983 聚合邊 |
| Hemibrain | 部分中央腦，含 mushroom body、central complex；neuPrint 等工具 | 適合導航子迴路分析，但不涵蓋完整感覺輸入系統 |
| MANC | 雄果蠅腹神經索、約 23,000 神經元 | 適合運動下游研究；不是雌果蠅 FAFB 同一個體，ID 不可直接拼接 |
| MaleCNS | 官方提供中央腦、視葉、腹神經索與 flat-connectome 下載 | 後續研究腦到運動系統的替代資料；本次未下載或量測 |

資料來源：

- [FlyWire 官方](https://home.flywire.ai/)、[Connectome Data Explorer](https://codex.flywire.ai/)。注意這個 Codex 是神經資料網站名稱。
- [FlyWire connectivity archive](https://zenodo.org/records/10676866)。本次使用模型 GitHub 檔案，沒有使用其 Feather 檔。
- [Shiu 團隊程式與資料](https://github.com/philshiu/Drosophila_brain_model)。
- [Hemibrain](https://www.janelia.org/project-team/flyem/hemibrain)。
- [MANC](https://www.janelia.org/node/68782)。
- [MaleCNS 官方下載](https://male-cns.janelia.org/download/)。

Connectome 是結構限制，並沒有完整提供活體膜電位、所有受體、突觸動態、學習規則或個體記憶。
神經元模型與遊戲感測／動作的配置仍是額外假設。腦 connectome 也不等於完整身體運動系統。

## 模擬器比較

| 工具 | 適用性 | 此次處理 |
|---|---|---|
| Shiu + Brian2 | 有論文依據、可作動態方程與放電統計參考 | 讀過模型原始碼；未聲稱復現原論文，未安裝 Brian2 |
| Brian2CUDA | 產生 CUDA 程式、適合加速 spiking 模擬；需編譯與 CUDA 環境 | 後續候選，需處理持久狀態與遊戲逐步輸入 |
| Eon fly-brain | 提供 Brian2、PyTorch、GeNN、NEST GPU 等比較入口；上游說明曾在 WSL2/RTX 4070 測試 | 是可參考的全腦加速實作；未執行其 benchmark，也不把上游說法當本次測值 |
| 自製 SciPy LIF | 低依賴、容易逐次修改輸入與保存狀態 | 已實作，CPU 基線，適合小子圖；全腦目前過慢 |
| FlyGym / NeuroMechFly | 果蠅身體、感測、MuJoCo 環境 | Minecraft 玩家取代身體，第一版不需要這個依賴；未執行 |

來源：

- [Shiu et al., Nature 2024](https://www.nature.com/articles/s41586-024-07763-9)。
- [Brian2](https://github.com/brian-team/brian2)、[Brian2CUDA](https://github.com/brian-team/brian2cuda)。
- [Eon fly-brain](https://github.com/eonsystemspbc/fly-brain)。該 repo 現行授權為 GPL-2.0-or-later；若未來直接移植程式須保留對應授權。本次未複製其實作。
- [NeuroMechFly](https://neuromechfly.org/)。

## 硬體結論與測試條件

已知筆電：32 GB RAM、2 × 1 TB SSD、RTX 5070。CPU、顯存容量、TGP、driver 尚未取得。
推估記憶體容量足以嘗試本專案的稀疏全腦模型；並非全腦即時運作的保證。
磁碟不是此原型主要限制，不需要下載電子顯微鏡原始影像。

本次全腦矩陣約 116 MiB，連同狀態會更大，匯入時也有中間表格與矩陣副本。
不要儲存每個時間步的全腦活動：只保留輸出群統計、有限長 spike window 及效能紀錄。
測試先用小型平地世界，讓 Minecraft、Windows 與模擬各有記憶體餘裕。

RTX 50 系列 GPU 的軟體支援需確認 Blackwell 與目前 driver 相容性；不能照搬舊 RTX 4070 的環境。
[PyTorch 2.7 官方公告](https://pytorch.org/blog/pytorch-2-7/) 是 Blackwell / CUDA 12.8 支援的歷史依據。
GPU 階段安裝時應依[官方安裝頁](https://pytorch.org/get-started/locally/)選擇當時相容版本。
本版不安裝 PyTorch，因此沒有假稱「已使用 5070」。

Minecraft 介面採 [Mineflayer](https://github.com/PrismarineJS/mineflayer) 的 `setControlState` 與 `look`。
本次固定套件 4.39.0；[官方 API](https://github.com/PrismarineJS/mineflayer/blob/master/docs/api.md)。
整合測試使用 [Flying Squid](https://github.com/PrismarineJS/flying-squid) 1.12.0 的 1.16.5 協定伺服器。
