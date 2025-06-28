# AllInn Tools

データ分析と自動化のための CLI ツールコレクション

## 概要

AllInn Tools は、データ分析や自動化タスクを効率化するための拡張可能な CLI ツールセットです。Python Fire を使用して、直感的で強力なコマンドラインインターフェースを提供します。

## インストール

### 前提条件

- Python 3.11 以上
- uv パッケージマネージャー（推奨）

### セットアップ

```bash
# リポジトリをクローン
git clone <repository-url>
cd allinn-tools

# 仮想環境の作成
uv venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係のインストール
uv pip install -e .

# 環境変数の設定
cp .env.sample .env
# .env ファイルを編集して ESTAT_API_KEY を設定
```

## 基本的な使い方

```bash
# 利用可能なコマンドを確認
allinn list_commands

# ヘルプを表示
allinn --help
allinn <command> --help

# コマンド実行例
allinn shinkansen --output results.csv
```

## 利用可能なコマンド

### shinkansen

新幹線停車駅の人口・面積・人口密度データを収集してCSVファイルを生成します（e-Stat API使用）。

```bash
# 基本的な使用方法（.env ファイルでAPIキー設定済み）
allinn shinkansen

# APIキーを直接指定（.env ファイルを使わない場合）
allinn shinkansen --api_key "your_api_key_here"

# オプション付きでの実行
allinn shinkansen --output custom.csv --route_filter "東海道,山陽" --sleep 1.0
```

**パラメータ:**

- `--output`: 出力CSVファイルパス（デフォルト: `shinkansen_population_density.csv`）
- `--route_filter`: 対象路線をカンマ区切りで指定（例: `"東海道,山陽"`）
- `--sleep`: e-Stat APIへのリクエスト間隔（秒、デフォルト: 0.5）
- `--api_key`: e-Stat API キー（.env ファイルの `ESTAT_API_KEY` からも取得可能）

**注意:** e-Stat API キーが必要です。[こちら](https://www.e-stat.go.jp/api/)から取得し、`.env` ファイルに設定してください。

詳細な仕様については [docs/shinkansen.md](docs/shinkansen.md) を参照してください。

## プロジェクト構造

```
allinn_tools/
├── __init__.py          # パッケージ初期化
├── __main__.py          # モジュール実行エントリーポイント
├── cli.py               # Fire ベースの CLI メインクラス
├── core/
│   ├── __init__.py
│   └── base_command.py  # コマンド基底クラス
└── commands/
    ├── __init__.py
    └── shinkansen.py    # 新幹線コマンド実装
```

## 新しいコマンドの追加

AllInn Tools は高い拡張性を持つよう設計されています。新しいコマンドを追加するには：

### 1. コマンドクラスの作成

`allinn_tools/commands/` に新しいファイルを作成：

```python
from ..core.base_command import BaseCommand

class YourCommand(BaseCommand):
    @property
    def name(self) -> str:
        return "yourcommand"
    
    @property
    def description(self) -> str:
        return "Your command description"
    
    def run(self, arg1: str, arg2: int = 10):
        """Main command logic here"""
        self.logger.info(f"Running with {arg1}, {arg2}")
        return "result"
```

### 2. CLI クラスへの登録

`allinn_tools/cli.py` の `AllInnCLI` クラスに新しいメソッドを追加：

```python
def yourcommand(self, arg1: str, arg2: int = 10):
    """Your command description"""
    cmd = YourCommand()
    return cmd.run(arg1=arg1, arg2=arg2)
```

### 3. コマンドリストへの追加

`cli.py` の `_commands` 辞書に追加：

```python
self._commands: Dict[str, Type[BaseCommand]] = {
    'shinkansen': ShinkansenCommand,
    'yourcommand': YourCommand,  # 追加
}
```

## 開発

### テストの実行

```bash
# テスト環境のセットアップ
uv pip install -e ".[dev]"

# テスト実行
pytest
```

### コードフォーマット

```bash
# フォーマッターとリンターを実行
black allinn_tools/
flake8 allinn_tools/
```

## ライセンス

[LICENSE ファイルを参照](LICENSE)

## 貢献

プルリクエストやイシューの報告を歓迎します。貢献する前に、開発ガイドラインをご確認ください。

## サポート

- 問題やバグの報告: [GitHub Issues](issues)
- 機能要望: [GitHub Discussions](discussions)
- ドキュメント: [docs/](docs/)

## 関連ドキュメント

- [新幹線コマンド仕様](docs/shinkansen.md)
- [API リファレンス](docs/api.md)（準備中）
- [開発者ガイド](docs/development.md)（準備中）