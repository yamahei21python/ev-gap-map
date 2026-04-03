# EV Charge Gap Map (EV充電スタンド 普及格差マップ)

![EV Gap Map Hero](public/landing_hero.png)

## プロジェクト概要
このプロジェクトは、日本国内の **EV（電気自動車）充電スタンドの設置状況** と **居住人口密度** を重ね合わせ、充電インフラの「充足」と「不足」を可視化するデータ分析プロジェクトです。

特定の地域において、人口に対して充電スタンドが十分に足りているか、あるいは不足している（ギャップがある）かを地図上で直感的に把握することを目指しています。

## 主な機能
1.  **EVスタンドデータの収集 (Scraper)**
    *   `gogo.gs` から最新の充電スタンド情報をスクレイピングで取得。
    *   CHAdeMO（急速）、200V（普通）などの出力タイプ別にデータを分類。
2.  **人口メッシュデータの取得 (Population Data)**
    *   e-Stat API を利用し、1km/500mメッシュ単位の統計人口データを取得。
3.  **ギャップ分析 (Gap Analysis)**
    *   各メッシュ内の人口と、周辺の充電スタンド数から「普及スコア」を算出。
4.  **インタラクティブ・マップ (Visualization)**
    *   Leaflet.js を使用し、ブラウザ上で閲覧可能なヒートマップ（GeoJSON）を生成。
5.  **GitHub Actions による自動更新**
    *   データの定期更新、ジオコーディング、マップ生成、デプロイを自動化。

## セットアップ

### 必要条件
*   Python 3.10以上
*   SQLite3

### インストール
```bash
git clone https://github.com/yamahei21python/ev-gap-map.git
cd ev-gap-map
pip install -r requirements.txt
```

## 使い方 (CLI)

メインエントリポイントは `main.py` です。

### 1. 充電スタンドデータの取得
```bash
# 全都道府県のデータを更新（続きから再開）
python3 main.py scrape --resume

# 特定の都道府県 (例: 東京都=13) の1ページ目だけ取得
python3 main.py scrape --prefecture 13 --max-pages 1
```

### 2. 人口データの取得
```bash
# e-Statから人口メッシュデータを取得してDBに保存
python3 main.py fetch-pop
```

### 3. ジオコーディング (住所の緯度経度化)
```bash
# 取得したスタンド住所から緯度経度を算出
python3 main.py geocode

# 人口メッシュの地名補完 (OSM Nominatim API)
python3 population/geocode_mesh.py
```

### 4. ギャップマップの生成
```bash
# 解析を実行し、public/data/gap_map.geojson を作成
python3 main.py gap-map
```

## ディレクトリ構造
*   `scraper/`: 充電スタンドのスクレイピング・DB管理
*   `population/`: 人口データの取得・地名変換・ギャップ分析ロジック
*   `data/`: SQLiteデータベース（`ev_chargers.db`, `population.db`）
*   `public/`: フロントエンド（HTML/CSS/JS）および生成されたGeoJSON
*   `.github/workflows/`: 自動更新パイプライン

## データ引用元
*   [gogo.gs](https://ev.gogo.gs) (EV充電スタンド情報)
*   [e-Stat 政府統計の総合窓口](https://www.e-stat.go.jp/) (国勢調査・人口メッシュ統計)
*   [OpenStreetMap (Nominatim)](https://nominatim.openstreetmap.org/) (ジオコーディング)

---
Developed by [yamahei21python](https://github.com/yamahei21python)
