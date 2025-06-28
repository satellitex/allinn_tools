# shinkansen コマンド仕様書

**新幹線停車駅 × 自治体人口密度 CSV ジェネレータ**

| 項目        | 内容                        |
| --------- | ------------------------- |
| ドキュメント版数  | v3.0（2025-06-28 更新）       |
| 作業対象リポジトリ | `allinn_tools/` |
| オーナー      | Takumi Yamashita          |
| 想定読者      | 開発者、データアナリスト、運用担当         |

---

## CLI 使用方法

### 基本的な使用方法

```bash
# .env ファイルに API キーを設定（推奨）
cp .env.sample .env
# .env ファイルを編集: ESTAT_API_KEY=your_api_key_here

# AllInn Tools CLI経由で実行
allinn shinkansen

# パラメータ付きで実行
allinn shinkansen --output custom.csv --route_filter "東海道,山陽" --sleep 1.0

# APIキーを直接指定する場合
allinn shinkansen --api_key "your_api_key_here"

# ヘルプ表示
allinn shinkansen --help
```

### パラメータ

| パラメータ | 型 | デフォルト値 | 説明 |
|-----------|-----|-------------|------|
| `--output` | string | `shinkansen_population_density.csv` | 出力CSVファイルパス |
| `--route_filter` | string | None | 対象路線をカンマ区切りで指定（例: `"東海道,山陽"`） |
| `--sleep` | float | 0.5 | e-Stat API へのリクエスト間隔（秒） |
| `--api_key` | string | None | e-Stat API キー（.env ファイルの `ESTAT_API_KEY` からも取得可能） |

### 使用例

```bash
# .env ファイルでAPIキーを設定して実行（推奨）
allinn shinkansen

# APIキーを直接指定
allinn shinkansen --api_key "your_api_key_here"

# 特定路線のみ（.env設定済み）
allinn shinkansen --route_filter "東海道"

# 複数路線を指定
allinn shinkansen --route_filter "東海道,山陽,九州"

# カスタム出力先とスリープ時間
allinn shinkansen --output "results/population_data.csv" --sleep 1.0

# 高速実行（API制限に注意）
allinn shinkansen --sleep 0.1
```

### e-Stat API キーの取得

1. [e-Stat ポータルサイト](https://www.e-stat.go.jp/api/) にアクセス
2. アカウント登録を行う
3. API利用申請を提出
4. 承認後、APIキーを取得
5. `.env.sample` をコピーして `.env` ファイルを作成
6. `.env` ファイルに `ESTAT_API_KEY=取得したAPIキー` を設定

---

### 1. 背景と目的

* **目的**：全国約 133 駅の新幹線停車駅を「路線別・人口密度順」に並べた CSV ファイル `shinkansen_population_density.csv` を自動生成し、市場規模推定や不動産／観光分析に活用可能なベースデータを素早く得る。e-Stat API を使用することで正確で最新の統計データを取得する。
* **理由**：複数路線や地方自治体を横断した比較指標が公的統計では一元化されておらず、手作業集計は非効率。e-Stat API により公式統計データへの直接アクセスが可能。

### 2. 成果物

| ファイル／成果物                            | 役割                                                                                            |
| ----------------------------------- | --------------------------------------------------------------------------------------------- |
| `shinkansen_population_density.csv` | 主要アウトプット。列: `route, station, municipality, prefecture, population, area_km2, population_density_km2, rank_in_route` |
| `allinn_tools/commands/shinkansen.py` | e-Stat API を使用したデータ収集＆整形コマンド実装                                                                         |
| `allinn_tools/cli.py`               | CLI エントリーポイント（Fire ベース）                                                                    |
| `inputs/shinkansen/shinkansen_stations.json` | 新幹線駅マスターデータ                                                                    |
| `uv.lock` / `pyproject.toml`        | 再現可能な環境定義                                                                                     |
| `README.md`                         | セットアップ・使用方法・FAQ                                                                               |
| `tests/`                            | パーサユニットテスト、統合テスト                                                                              |

### 3. スコープ

#### 3.1 機能要件

1. **ステーションマスター取得**

   * ソース: `inputs/shinkansen/shinkansen_stations.json`（路線・駅・自治体・都道府県を網羅）
2. **人口・面積・人口密度取得**

   * データソース: e-Stat API（SSDS基礎データ 2020年）
   * 取得データ: A1101=総人口、B1101=総面積、人口密度は自動計算（人口÷面積）
   * 統計表ID: 
     - 人口データ: 0000020201（社会・人口統計体系 市区町村データ A. 人口・世帯）
     - 面積データ: 0000020102（社会・人口統計体系 市区町村データ B. 自然環境）
   * 自治体コードマッピングによる正確なデータ取得
   * 2つのAPIコールでデータを統合し、完全なデータセットを構築
3. **API アクセス制御**

   * e-Stat API キーによる認証
   * 0.5 s スリープ／リクエスト、全国データを一括取得しメモリキャッシュ
   * 環境変数またはコマンドライン引数でのAPIキー指定
   * 人口と面積データを2回のAPIコールで効率的に取得
4. **ランキング付け**

   * 路線内で人口密度降順に並べ、`rank_in_route` を付与
5. **CSV 出力**

   * UTF-8、ヘッダ付き、指定パスへ保存
   * 拡張カラム: `population`, `area_km2`, `population_density_km2`
6. **CLI オプション**

   * `--output`: 出力先パス
   * `--route-filter`: 路線名複数指定（部分生成用）
   * `--sleep`: リクエスト間隔秒数
   * `--api-key`: e-Stat API キー
7. **環境構築**

   * 依存管理は **uv** を使用（下記 §4）
8. **テスト**

   * e-Stat API レスポンスパーサが想定データを返すこと
   * 主要 3 駅（東京・新大阪・博多）で CSV 行フォーマットが正しいこと

#### 3.2 非機能要件

| 区分    | 要件                                       |
| ----- | ---------------------------------------- |
| 性能    | フル実行時間 ≤ 3 分（平均回線・キャッシュ無の場合）             |
| 可搬性   | Python 3.8+ / macOS, Linux, Windows で動作 |
| ロギング  | `INFO`：進行状況、`WARNING`：空値検出、`ERROR`：致命的中断 |
| 再現性   | `uv.lock` 準拠で誰でも同一環境を再構築可能               |
| 法令・倫理 | e-Stat API 利用規約を遵守、適切なAPIキー管理    |

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

# 環境変数の設定
cp .env.sample .env                     # .env ファイルを作成
# .env ファイルを編集して ESTAT_API_KEY を設定
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
├─ .env.sample            # 環境変数設定サンプル
├─ .env                   # 環境変数設定（Git除外）
├─ .gitignore             # Git除外設定
├─ pyproject.toml         # [project] & [tool.uv] 定義
├─ uv.lock
├─ README.md
└─ docs/
   └─ shinkansen.md       # 本ドキュメント
```

### 6. システムフロー

1. **Load Environment** → `.env` ファイルから環境変数を読み込み
2. **Load Station List** → JSON パース（`inputs/shinkansen/shinkansen_stations.json`）
3. **API Key Validation** → `.env` ファイルまたはコマンドライン引数から取得
4. **For each municipality** → キャッシュ有無判定
5. **e-Stat API Call** → 人口データ取得（0000020201）→ 面積データ取得（0000020102）→ データ統合
6. **Data Processing** → 人口・面積データ統合、人口密度自動計算
7. **Append record** → pandas DataFrame へ蓄積
8. **Group & Rank** → `groupby('route').cumcount()`
9. **Output CSV** → 拡張カラム対応

### 7. エラーハンドリング

| ケース          | 処理                                       |
| ------------ | ---------------------------------------- |
| API キー未設定 | エラーメッセージとAPIキー取得方法を表示して終了 |
| e-Stat API エラー | `ERROR` ログ、処理中断（現在は100%取得成功率を実現）|
| 自治体コード未登録 | `WARNING` ログ、同上                          |
| 出力不可         | 例外をスローしプロセス終了（CI で検知）                    |

### 8. テスト方針

* **ユニット**: e-Stat API レスポンス解析が各パターンを正確に処理
* **結合**: ステーション 10 件限定モードで実行→CSV 行数 & 列検証
* **CI**: GitHub Actions (`python: 3.11 / 3.12`) で `uv pip sync && pytest`
* **API モック**: テスト環境での e-Stat API モック化

### API統合の詳細

```python
# 統計表ID構成
POPULATION_STATS_ID = "0000020201"  # A. 人口・世帯データ  
AREA_STATS_ID = "0000020102"        # B. 自然環境データ

# データ取得フロー
1. 人口データ一括取得 (A1101: 総人口)
2. 面積データ一括取得 (B1101: 総面積) 
3. メモリ内でデータ統合
4. 人口密度計算 (population ÷ area)
5. 路線別ランキング生成
```

利用統計表の詳細：
- **統計コード**: 00200502 (社会・人口統計体系)
- **データ年**: 2020年 (利用可能な最新年)
- **地域コード**: JIS X 0402準拠の5桁市区町村コード

### 9. 今後の拡張余地（参考）

| 項目       | 概要                                         |
| -------- | ------------------------------------------ |
| ~~面積データAPI~~ | ✅ **完了**: e-Stat API から面積データを取得済み |
| 自治体コード拡充 | 全自治体の統計コードマッピングを網羅 |
| キャッシュ永続化 | `sqlite` or `parquet` に保存し、後続分析パイプラインで再利用  |
| 追加カラム    | 駅緯度経度、開業年、日平均乗降客数、路線距離 etc.                |
| WebUI    | Streamlit／Next.js＋API でインタラクティブ可視化         |

### 10. 受け入れ基準

1. `uv pip install -e .` 後、e-Stat API キー設定して `allinn shinkansen` を実行すると終了コード 0。
2. `shinkansen_population_density.csv` が 130 行以上・8 列で生成。
3. 人口・面積・人口密度データがすべて取得され、欠損率 0%。
4. CLI パラメータ（`--output`, `--route_filter`, `--sleep`, `--api_key`）が正常に動作。

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

**問題**: e-Stat API キーエラー
**解決**: 
```bash
# .env ファイルに正しいAPIキーを設定
echo "ESTAT_API_KEY=your_valid_api_key" > .env
# または直接指定
allinn shinkansen --api_key "your_valid_api_key"
```

**問題**: e-Stat API への接続エラー
**解決**: 
```bash
# スリープ時間を増やして再試行
allinn shinkansen --sleep 2.0
```

**問題**: 特定の自治体で人口データが取得できない
**解決**: ログを確認し、自治体コードマッピングが正しいか確認。未対応の自治体は手動でコードを追加する必要があります。

## CSV出力例

東海道新幹線での実行結果（人口密度順）：

```csv
route,station,municipality,prefecture,population,area_km2,population_density_km2,rank_in_route
東海道新幹線,品川,港区,東京都,260486.0,20.37,127.88,1
東海道新幹線,新大阪,大阪市,大阪府,2752412.0,225.32,122.16,2
東海道新幹線,新横浜,横浜市,神奈川県,3777491.0,437.71,86.30,3
東海道新幹線,名古屋,名古屋市,愛知県,2332176.0,326.50,71.43,4
東海道新幹線,小田原,小田原市,神奈川県,436905.0,69.56,62.81,5
東海道新幹線,東京,千代田区,東京都,66680.0,11.66,57.19,6
...
```

### データ取得成功率

- **人口データ**: 100% (0件の欠損)
- **面積データ**: 100% (0件の欠損)  
- **人口密度**: 100% (自動計算による完全データ)
