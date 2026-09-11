# v0.2 玩家模式

這一階段讓原型能活動於更複雜地形，並接受一個明確的社交目標：跟隨指定玩家。
神經部分仍為真實六神經元 probe；目前沒有訓練、長期記憶、合成、採礦或戰鬥。

## 更新與啟動

先停止舊 bot 與神經服務。使用 ZIP 的話，下載 GitHub 最新 ZIP 並解壓到新的資料夾，
依 README 建立 venv 與安裝依賴，避免覆蓋自己修改過的檔案。
使用 git clone 的話，先保留自己的修改，再 `git pull --ff-only` 更新。

終端 A 照常啟動神經服務：

```powershell
.\.venv\Scripts\python.exe -m flycraft.server --bundle fixtures/probe --mapping fixtures/probe/mapping.json
```

終端 B 設定好 README 的 Minecraft 連線環境變數後：

```powershell
npm --prefix bridge start
```

在 **終端 B** 輸入指令並按 Enter（不是 Minecraft 聊天欄）：

| 指令 | 行為 |
|---|---|
| `roam` | 自主前進與神經避障，這是啟動預設模式 |
| `follow Senuil` | 跟隨此精確 Minecraft 玩家名稱；請換成你的遊戲 ID |
| `stop` | 立即清除前進／跳躍，進入待機；包含轉向也停止 |
| `status` | 在終端顯示模式、目標距離、危險與最近動作理由 |
| `help` | 顯示指令 |
| `quit` | 離開伺服器並結束 bot；Ctrl+C 也可以 |

模式切換使舊神經 HTTP 回覆失效，下一次建立新的神經 session，避免舊指令讓停止中的 bot 重新移動。
程式不在遊戲聊天欄發送任何訊息。

## 行為規則與限制

- **跳躍：** 前方 0.85 格的玩家寬度範圍出現一格實體障礙、上方有空間、腳下著地且神經輸出允許前進時跳躍。兩格高牆不跳。每次跳躍至少間隔 700 ms。
- **落差：** 前方目前腳高度以下一格和兩格的支撐檢查皆無實體方塊時，禁止前進。正常情況容許一格下降。這是局部取樣，不能保證高速、外力推動或所有特殊方塊上的安全。
- **危險：** 前方／落腳區檢查水、岩漿、火、仙人掌、岩漿塊、營火、甜莓叢、粉雪等；水也暫時列為停止區，尚未做游泳。未載入區塊保守停止。
- **卡住：** 約 1.5 秒沒有達到 0.25 格水平進展、且仍有移動意圖或受到阻擋時，原地轉向約 1.1 秒再嘗試。這是有限的恢復規則，不保證走出迷宮或所有牆角。
- **跟隨：** 目標需是目前載入的玩家實體。保持約 2.5 格距離；超過 24 格、消失或高度差超過 3 格時等待。先朝向目標，再前進。障礙可能使它無法抵達，沒有繞路規劃或傳送。
- **安全更新：** 即使神經請求還沒回覆，也會在 physicsTick 檢查前方危險並停止。

半磚、樓梯、門、圍牆等特殊碰撞形狀沒有精細處理；先在全方塊平地／台階測試。
跟隨目標的資料來自遊戲實體座標，不是果蠅視覺辨認，也沒有遮蔽物視線辨識。

## 哪些由神經網路控制？

| 決策 | 來源 |
|---|---|
| 基本前進訊號與轉向速度 | 真實 probe 的輸出神經元放電率 |
| 目標方向 → 左右刺激 | 人工感覺編碼，經輸入細胞與真實連線再讀出 |
| 暫時忽略可跳台階的左右障礙刺激 | 工程感測預處理 |
| 跳躍、距離停止、坑洞／危險停止、卡住轉向 | 工程輔助 |

日誌保留 `rates_hz`（神經輸出）和 `player.reason`（最終執行理由），方便區分。
例如神經 `forward=true` 但執行結果 `player.forward=false`，可能是 `drop` 或 `near-target` 阻止前進。

## 測試

```powershell
npm --prefix bridge test
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/test_minecraft.py --scenario wall
.\.venv\Scripts\python.exe scripts/test_minecraft.py --scenario step
.\.venv\Scripts\python.exe scripts/test_minecraft.py --scenario drop
.\.venv\Scripts\python.exe scripts/test_minecraft.py --scenario follow
```

四個情境使用隔離的 Flying Squid 1.16.5 網路伺服器、正式 bot 入口及真實 probe。
Windows／Paper 1.21.9 仍需本機驗收。

接下來的玩家能力可以逐級做成「找資源 → 採集 → 撿拾 → 使用工具 → 合成 → 生存目標」。
每加入一種動作都保留其來源標記與消融對照，讓果蠅神經控制不會被越來越多輔助功能掩蓋。
