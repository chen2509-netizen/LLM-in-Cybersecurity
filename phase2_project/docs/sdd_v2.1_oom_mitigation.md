# 系統變更設計文件 (SDD Extension)：feat_v2.1_OOM_solution.md

## 1. 變更背景與問題量化 (Change Background & Problem Quantization)

本文件定義 Phase 2 Pipeline 在處理大規模資安日誌（數據量達 $1,533,064$ 筆）時的架構變更規格，旨在消除現行設計中的記憶體溢出（Out of Memory, OOM）風險與效能卡死問題。現行組件之技術瓶頸量化分析如下：

* **運算裝置模糊性**：現行 `EmbeddingAdapter` 未明確指定底層模型載入之硬體裝置（`device` 參數），導致在特定生產環境下回退至 CPU 執行。此外，因關閉進度觀測指標（`show_progress_bar=False`），致使巨量資料編碼時主流程呈現定格狀態，缺乏監控度。
* **分群空間複雜度爆炸**：現行 `ClusteringAdapter` 採用 `scikit-learn` 原生 `DBSCAN`。當配置參數 `metric="cosine"` 時，該實作無法啟用空間索引樹（如 KD-Tree 或 Ball-Tree）進行剪枝加速，其空間複雜度呈 Worst-case $O(n^2)$。
* **極限記憶體開銷估算**：在樣本數 $n = 1,533,064$ 下，若建構完整成對距離矩陣（Pairwise Distance Matrix），理論開銷量化如下：
* `float64` 精度：$(1,533,064)^2 \times 8 \text{ Bytes} \approx 18.80 \text{ TB}$ (約 $17.10 \text{ TiB}$)
* `float32` 精度：$(1,533,064)^2 \times 4 \text{ Bytes} \approx 9.40 \text{ TB}$ (約 $8.55 \text{ TiB}$)


此幾何級數增長之空間需求必將觸發作業系統之強制終止機制（OOM Killer）。必須重構組件行為規格，嚴禁在百萬級規模下採用原生 CPU DBSCAN 計算路徑。

---

## 2. 向量化轉接器規格變更 (src/adapters/embedding_adapter.py)

### 2.1 介面與行為規範

`EmbeddingAdapter` 必須在維持既有外部調用介面不變的前提下，優化內部延遲載入（Lazy Load）與編碼執行期之行為：

1. **動態硬體執行裝置分流**：
* 在初始化或模型延遲載入階段，必須引入硬體加速偵測機制。
* 若環境支援 CUDA 驅動及硬體，模型載入裝置參數必須明確指定為 `"cuda"`。
* 若 CUDA 環境不可用，則安全降級（Fallback）至 `"cpu"` 執行。


2. **進度條觀測性啟用**：
* `encode()` 方法內部呼叫底層模型時，參數 `show_progress_bar` 必須變更為 `True`。
* 確保標準輸出（stdout）能即時接收串流編碼之百分比與時程預估，提供外部監控指標。



### 2.2 內部控制邏輯變更規格

| 執行階段 | 現行行為 | 變更後標準規格 |
| --- | --- | --- |
| **模型初始化 (Lazy Load)** | 未指定 `device` 參數，依賴庫預設行為。 | 檢驗 `torch.cuda.is_available()`，動態賦予 `"cuda"` 或 `"cpu"` 至模型載入參數。 |
| **編碼執行 (Encode)** | `show_progress_bar=False` | `show_progress_bar=True` |

---

## 3. 分群轉接器規格變更 (src/adapters/clustering_adapter.py)

### 3.1 核心加速技術與內存控制

為適配限制型硬體環境（目標環境：RTX 3060 12GB VRAM），分群核心必須引入 NVIDIA RAPIDS 體系之 `cuML` 加速庫，替換原生 CPU 運算組件。變更規格如下：

1. **記憶體分塊控制限制**：
* 引入顯存分塊控制參數 `max_mbytes_per_batch`，其數值必須固定配置為 `4096`（即 4GB）。
* 此參數用於限制單次 pairwise distance 批次計算之記憶體配額，降低 RTX 3060 12GB VRAM 環境下的 OOM 風險；但不構成整體演算法總顯存使用量上限，最終可行性仍需依實測基準確認。


2. **輸出數據類型相容性**：
* 配置 `output_type="numpy"`，確保加速組件回傳之標籤矩陣型態與現有下游數據流無縫相容。



### 3.1.1 顯存控制限制聲明

`max_mbytes_per_batch=4096` 僅限制 `cuML DBSCAN` 於 pairwise distance computation 階段的批次記憶體目標，不代表整體演算法總顯存使用量上限。由於 DBSCAN 仍需依據 `eps`、資料局部密度與鄰接圖規模產生額外中間資料結構，因此本參數僅定義為 OOM 風險降低機制，不得描述為 12GB VRAM 環境下的完成保證。

### 3.2 巨量資料 Fail-Fast 安全熔斷機制

嚴禁盲目容許高負載資料直接回退至 `sklearn.cluster.DBSCAN`。系統必須依據輸入數據規模（$n = \text{embeddings.shape}[0]$）實施雙軌分流控制與安全熔斷策略：

* **低資料量級軌道（$n \le 10,000$）**：
* 若系統未安裝 `cuML` 套件，允許 Fallback 至 `sklearn.cluster.DBSCAN`。
* 必須顯式配置 `n_jobs=-1` 以啟用全核心多執行緒加速，維持非 GPU 環境下的基礎交叉驗證能力。


* **高資料量級軌道（$n > 10,000$）**：
* 系統執行前置檢查，若環境未成功配置 `cuML` 加速套件，**必須立即拋出 `RuntimeError` 終止當前 Pipeline 流程**。
* 實施安全熔斷，嚴禁進入 CPU 巨量成對距離計算，防止系統發生永久性卡死。



$n\_samples \le 10,000$ 為本專案保守工程熔斷閾值，用於限制 `sklearn fallback` 的最大輸入規模；該數值非 `scikit-learn` 官方保證之記憶體安全邊界，亦非 DBSCAN 演算法之理論上限。

### 3.3 分群執行期控制流規格

```
[輸入: embeddings (n_samples)]
       │
       ├─► 若 n_samples == 0 ──► 回傳空陣列
       │
       └─► 檢查環境是否存在 cuML 模組 (HAS_CUML)
             │
             ├──► [TRUE] ──► 實例化 cuDBSCAN
             │               配置: max_mbytes_per_batch=4096, output_type="numpy"
             │               執行 fit_predict() ──► 輸出結果
             │
             └──► [FALSE] ──► 檢查資料量級
                                │
                                ├──► 若 n_samples <= 10000 ──► Fallback 至 sklearn DBSCAN
                                │                             (工程熔斷閾值，配置: n_jobs=-1)
                                │                             執行 fit_predict() ──► 輸出結果
                                │
                                └──► 若 n_samples > 10000 ──► 觸發安全熔斷
                                                              拋出 RuntimeError (拒絕執行並中斷)

```

---

## 4. 環境相依性與部署規格 (Environment & Deployment Specs)

### 4.1 部署環境依賴約束

部署命令應以 RAPIDS 官方 Release Selector 依實際 CUDA Driver、CUDA Runtime、Python 版本與 WSL2/Linux 發行版產生之結果為準。本文列出之 conda / pip 命令僅作為 CUDA 12.x + Python 3.10 基準環境之已知相容範例，不作為跨環境固定安裝命令，不應硬編碼為永久約束。環境配置腳本中嚴禁採用泛用型 `pip install cuml` 命令。

* **相容環境範例 A（Conda 渠道安裝）**：
```bash
conda install -c rapidsai -c conda-forge -c nvidia cuml=24.04 python=3.10 cuda-version=12.2

```


* **相容環境範例 B（NVIDIA PyPI 渠道安裝）**：
```bash
pip install --extra-index-url https://pypi.nvidia.com cuml-cu12==24.4.*

```



### 4.2 品質與效能矩陣判定

* **架構非邊緣性判定**：事件分群階段位於整個 Pipeline 資料流的核心環節（Embedding $\to$ Clustering $\to$ Evaluator），此優化規格直接關係到後續評估報告與格式化輸出的完整性，定義為系統核心變更。
* **執行時程不確定性標記**：[不確定] <由於未實際在 RTX 3060 12GB 上執行 153 萬筆資料的 cuML DBSCAN 完整測試，最終執行時間受 eps 與資料局部密度影響，無法給出確定的耗時結論，需依賴實測基準。>
