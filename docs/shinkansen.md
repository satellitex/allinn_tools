# shinkansen コマンド仕様書

**新幹線停車駅 × 自治体人口密度 CSV ジェネレータ**

| 項目        | 内容                        |
| --------- | ------------------------- |
| ドキュメント版数  | v2.0（2025-06-28 更新）       |
| 作業対象リポジトリ | `allinn_tools/` |
| オーナー      | Takumi Yamashita          |
| 想定読者      | 開発者、データアナリスト、運用担当         |

---

## CLI 使用方法

### 基本的な使用方法

```bash
# AllInn Tools CLI経由で実行
allinn shinkansen

# パラメータ付きで実行
allinn shinkansen --output custom.csv --route_filter "東海道,山陽" --sleep 1.0

# ヘルプ表示
allinn shinkansen --help
```

### パラメータ

| パラメータ | 型 | デフォルト値 | 説明 |
|-----------|-----|-------------|------|
| `--output` | string | `shinkansen_population_density.csv` | 出力CSVファイルパス |
| `--route_filter` | string | None | 対象路線をカンマ区切りで指定（例: `"東海道,山陽"`） |
| `--sleep` | float | 0.5 | Wikipediaへのリクエスト間隔（秒） |

### 使用例

```bash
# 全路線のデータを生成
allinn shinkansen

# 特定路線のみ
allinn shinkansen --route_filter "東海道"

# 複数路線を指定
allinn shinkansen --route_filter "東海道,山陽,九州"

# カスタム出力先とスリープ時間
allinn shinkansen --output "results/density_data.csv" --sleep 1.0

# 高速実行（注意: Wikipediaサーバーへの負荷を考慮すること）
allinn shinkansen --sleep 0.1
```

---

### 1. 背景と目的

* **目的**：全国約 133 駅の新幹線停車駅を「路線別・人口密度順」に並べた CSV ファイル `shinkansen_population_density.csv` を自動生成し、市場規模推定や不動産／観光分析に活用可能なベースデータを素早く得る。
* **理由**：複数路線や地方自治体を横断した比較指標が公的統計では一元化されておらず、手作業集計は非効率。

### 2. 成果物

| ファイル／成果物                            | 役割                                                                                            |
| ----------------------------------- | --------------------------------------------------------------------------------------------- |
| `shinkansen_population_density.csv` | 主要アウトプット。列: `route, station, municipality, prefecture, population_density_km2, rank_in_route` |
| `allinn_tools/commands/shinkansen.py` | データ収集＆整形コマンド実装                                                                         |
| `allinn_tools/cli.py`               | CLI エントリーポイント（Fire ベース）                                                                    |
| `uv.lock` / `pyproject.toml`        | 再現可能な環境定義                                                                                     |
| `README.md`                         | セットアップ・使用方法・FAQ                                                                               |
| `tests/`                            | パーサユニットテスト、統合テスト                                                                              |

### 3. スコープ

#### 3.1 機能要件

1. **ステーションマスター取得**

   * ソース: GitHub raw `shinkansen_stations.json`（路線・駅・自治体・都道府県を網羅）
2. **人口密度取得**

   * 市・特別区: Wikipedia 「List of cities in Japan」「Special wards of Tokyo」で抽出
   * 町・村: 各自治体の個別ページ (`Infobox settlement`) から抽出
   * 取得値が `None` の場合はエラーリスト化し、処理継続
3. **レートリミット対策**

   * 0.5 s スリープ／リクエスト、同一自治体はメモ化キャッシュ
4. **ランキング付け**

   * 路線内で人口密度降順に並べ、`rank_in_route` を付与
5. **CSV 出力**

   * UTF-8、ヘッダ付き、指定パスへ保存
6. **CLI オプション（最低限）**

   * `--output`: 出力先パス
   * `--route-filter`: 路線名複数指定（部分生成用）
   * `--sleep`: リクエスト間隔秒数
7. **環境構築**

   * 依存管理は **uv** を使用（下記 §4）
8. **テスト**

   * 正規表現パーサが想定数値を返すこと
   * 主要 3 駅（東京・新大阪・博多）で CSV 行フォーマットが正しいこと

#### 3.2 非機能要件

| 区分    | 要件                                       |
| ----- | ---------------------------------------- |
| 性能    | フル実行時間 ≤ 3 分（平均回線・キャッシュ無の場合）             |
| 可搬性   | Python 3.11+ / macOS, Linux, Windows で動作 |
| ロギング  | `INFO`：進行状況、`WARNING`：空値検出、`ERROR`：致命的中断 |
| 再現性   | `uv.lock` 準拠で誰でも同一環境を再構築可能               |
| 法令・倫理 | robots.txt を尊重、Wikipedia への過度アクセスを避ける    |

### 4. 技術スタック & セットアップ

```bash
# uv をまだ導入していない場合のみ
pip install uv                          # or brew install uv

# AllInn Tools のセットアップ
git clone <repository-url>
cd allinn-tools
uv venv .venv                           # 仮想環境
source .venv/bin/activate               # Windows: .venv\Scripts\activate
uv pip install -e .                    # AllInn Tools をインストール
```

### 5. ディレクトリ構成

```
allinn-tools/
├─ allinn_tools/
│  ├─ __init__.py
│  ├─ __main__.py
│  ├─ cli.py              # Fire ベースの CLI
│  ├─ core/
│  │  ├─ __init__.py
│  │  └─ base_command.py  # コマンド基底クラス
│  └─ commands/
│     ├─ __init__.py
│     └─ shinkansen.py    # 新幹線コマンド実装
├─ inputs/
│  └─ shinkansen/
│     └─ shinkansen_stations.json  # 新幹線駅データ
├─ pyproject.toml         # [project] & [tool.uv] 定義
├─ uv.lock
├─ README.md
└─ docs/
   └─ shinkansen.md       # 本ドキュメント
```

### 6. システムフロー

1. **Load Station List** → JSON パース
2. **For each municipality** → キャッシュ有無判定
3. **HTTP GET to Wikipedia** → BeautifulSoup パース → 正規表現抽出
4. **Append record** → pandas DataFrame へ蓄積
5. **Group & Rank** → `groupby('route').cumcount()`
6. **Output CSV**

### 7. エラーハンドリング

| ケース          | 処理                                       |
| ------------ | ---------------------------------------- |
| HTTP 4xx/5xx | 3 回リトライ後 `population_density_km2 = None` |
| パーサ不一致       | `WARNING` ログ、同上                          |
| 出力不可         | 例外をスローしプロセス終了（CI で検知）                    |

### 8. テスト方針

* **ユニット**: `extract_density(text)` が各パターンを正確に返却
* **結合**: ステーション 10 件限定モードで実行→CSV 行数 & 列検証
* **CI**: GitHub Actions (`python: 3.11 / 3.12`) で `uv pip sync && pytest`

### 9. 今後の拡張余地（参考）

| 項目       | 概要                                         |
| -------- | ------------------------------------------ |
| 人口更新 API | e-Stat API で 5-年毎国勢調査数値を直接取得し、スクレイピング依存を解消 |
| キャッシュ永続化 | `sqlite` or `parquet` に保存し、後続分析パイプラインで再利用  |
| 追加カラム    | 駅緯度経度、開業年、日平均乗降客数、路線距離 etc.                |
| WebUI    | Streamlit／Next.js＋API でインタラクティブ可視化         |

### 10. 受け入れ基準

1. `uv pip install -e .` 後、`allinn shinkansen` を実行すると終了コード 0。
2. `shinkansen_population_density.csv` が 130 行以上・6 列で生成。
3. 自治体人口密度に `None` が 1 % 未満。
4. CLI パラメータ（`--output`, `--route_filter`, `--sleep`）が正常に動作。

### 11. トラブルシューティング

#### よくある問題

**問題**: `allinn: command not found`
**解決**: 
```bash
# 仮想環境がアクティブでない場合
source .venv/bin/activate

# または、モジュールとして実行
python -m allinn_tools shinkansen
```

**問題**: Wikipedia への接続エラー
**解決**: 
```bash
# スリープ時間を増やして再試行
allinn shinkansen --sleep 2.0
```

**問題**: 特定の自治体で人口密度が取得できない
**解決**: ログを確認し、取得失敗した自治体を手動で調査。将来的には e-Stat API 連携で解決予定。
