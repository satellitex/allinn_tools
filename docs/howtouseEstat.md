以下では **e-Stat API（3.0 版）** を使って、**全国すべての市区町村（現行 1,741 自治体）について 「総人口・総面積・人口密度」** を取得し、Python で CSV にまとめるまでの具体的な流れを Step-by-Step で整理します。

---

## 0. 前提

| 項目          | 内容                                                                                                                     |
| ----------- | ---------------------------------------------------------------------------------------------------------------------- |
| 対象統計表       | **社会・人口統計体系　市区町村データ　基礎データ（廃置分合処理済）**<br>‐ 表番号 **0000020201** （通称 “SSDS 基礎データ”）<br>‐ 統計コード 00200502 ([e-stat.go.jp][1]) |
| 収録指標（cat01） | A1101 = 総人口（人）<br>B1101 = 総面積（km²）<br>C1101 = 総面積1 km²当たり人口密度（人/km²）※ない年は A1101÷B1101 で自計算                             |
| 年度          | 最新年（例 2023 年）を指定。時系列を並べたい場合は `cdTime` を複数渡す                                                                            |
| API 同時セル上限  | 100 000 cell／リクエスト → 市区町村×3 指標（≈5200 cell）なので 1 回で取得可                                                                  |
| 認証          | e-Stat の **AppID**（無料、メール登録のみ）                                                                                         |

---

## 1. AppID を取得

1. e-Stat にログイン → 右上 **API** → 「API 利用申請」
2. 任意の名称で **AppID** を発行（即時）
   *以降のリクエストはすべて `appId=YOUR_APP_ID` を付与*

---

## 2. 目的の統計表 ID（statsDataId）を確認

```bash
# 0000020201 が既に分かっている場合はこの手順は省略可
curl -G https://api.e-stat.go.jp/rest/3.0/app/json/getStatsList \
  --data-urlencode "appId=YOUR_APP_ID" \
  --data-urlencode "statsCode=00200502" \
  --data-urlencode "searchWord=基礎データ" \
  --data-urlencode "surveyYears=2023" \
  --data-urlencode "searchKind=2"
```

レスポンス JSON の `statsDataId` が **0000020201** と取れる。([e-stat.go.jp][2])

---

## 3. メタ情報で分類コードをチェック（初回のみ）

```bash
curl -G https://api.e-stat.go.jp/rest/3.0/app/json/getMetaInfo \
  --data-urlencode "appId=YOUR_APP_ID" \
  --data-urlencode "statsDataId=0000020201"
```

`CLASS_OBJ` → `cat01` 部分に **A1101・B1101・C1101** 等があることを確認。
（ページ版サンプルにも同じコードが列挙されています）([e-stat.go.jp][3])

---

## 4. 統計データの取得

### 4-1. すべての市区町村 × 3 指標 × 最新年

```bash
curl -G https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData \
  --data-urlencode "appId=YOUR_APP_ID" \
  --data-urlencode "statsDataId=0000020201" \
  --data-urlencode "cdCat01=A1101,B1101,C1101" \
  --data-urlencode "cdTime=2023000000"   # ← 2023 年。年度は YYYY000000
  --data-urlencode "limit=100000"
```

* ポイント

  * `cdArea` を省略すると自治体すべてが返る
  * 返ってくる JSON 配列 `DATA` の要素数 ≒ 1 741 自治体 × 3 指標

### 4-2. ページングが必要なとき

大きい表を取る場合は `startPosition` と `limit` を追加し 10 万セル毎にループ。

---

## 5. Python（uv で環境固定）で CSV を吐き出す

```bash
# =======  ① one-time setup  =========================================
pip install uv           # 初回のみ
uv venv .venv
source .venv/bin/activate
uv pip install requests pandas tqdm

# =======  ② script  ==================================================
import requests, pandas as pd, itertools, time
APP_ID   = "YOUR_APP_ID"
SID      = "0000020201"
CAT      = ["A1101","B1101","C1101"]       # 人口・面積・人口密度
TIME     = "2023000000"                    # 2023 年
URL      = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"

params = {
    "appId": APP_ID, "statsDataId": SID,
    "cdCat01": ",".join(CAT), "cdTime": TIME,
    "limit": 100000
}

rows = requests.get(URL, params=params, timeout=30).json()\
               ["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]

rec = [{ "areaCode": r["@area"],                # 13101
         "cat01":    r["@cat01"],               # A1101 等
         "value":    r["$"] } for r in rows]

df = pd.DataFrame(rec)
wide = df.pivot(index="areaCode", columns="cat01", values="value")\
         .rename(columns={"A1101":"population",
                          "B1101":"area_km2",
                          "C1101":"density"})
wide.to_csv("municipality_pop_density_2023.csv", encoding="utf-8")
print("✅ CSV output:", wide.shape)
```

* `C1101` が無い年度は `density = population / area_km2` で自計算するだけ。
* `areaCode` は JIS X 0402 市区町村コード（5 桁＋特別区で 2 桁区部を含む）。

---

## 6. よくあるハマりどころ

| 症状                      | 原因と対策                                   |
| ----------------------- | --------------------------------------- |
| **403 Invalid AppID**   | AppID の typo／有効期限切れ（登録後 1 年）            |
| **400 Over limitation** | `limit` 超え ⇒ `startPosition` を併用し分割     |
| **cat01 取得できない**        | 指標コードが年度によって欠落 → まず `getMetaInfo` で存在確認 |
| **人口密度が NaN**           | 該当年度に `C1101` が無い（例：古い年）→ 自計算           |

---

## 7. 参考リンク

1. e-Stat API 利用ガイド（公式）([e-stat.go.jp][2])
2. SSDS 基礎データ（0000020201）データセット詳細ページ([e-stat.go.jp][1])
3. SSDS 指標コード一覧・計算式（人口密度＝A1101/B1101 等）([e-stat.go.jp][3])

---

### まとめ

* **statsDataId=0000020201** を使えば、市区町村単位の人口・面積・人口密度が **1 リクエスト** で取得できます。
* e-Stat の分類コード（cat01）を把握するために **getMetaInfo** を必ず最初に叩く。
* 容量制限は 10 万セル／回なので、指標を絞ればページング不要。

これで「新幹線駅 × 自治体人口密度 CSV ジェネレータ」も **e-Stat API 100% ソース化** できます。ご不明点があれば適宜どうぞ！

[1]: https://www.e-stat.go.jp/en/stat-search/database?statdisp_id=0000020201&utm_source=chatgpt.com "e-Stat Portal Site of Official Statistics of Japan"
[2]: https://www.e-stat.go.jp/api/api-dev/how_to_use?utm_source=chatgpt.com "APIの使い方 | 政府統計の総合窓口(e-Stat)−API機能"
[3]: https://www.e-stat.go.jp/koumoku/sihyo_keisansiki/A?utm_source=chatgpt.com "A 人口・世帯 - e-Stat 政府統計の総合窓口"
