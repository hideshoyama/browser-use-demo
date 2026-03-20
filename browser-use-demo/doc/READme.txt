# ファイル構成
browser-use-demo/
├── pyproject.toml         # uv 依存関係定義
├── .env.example           # API キーのテンプレート
├── .gitignore
├── companies.txt          # サンプル3社（トヨタ・ソニー・任天堂）
├── company_research.py    # メインスクリプト
└── README.md

#セットアップと実行手順

cd browser-use-demo

# 依存関係インストール
uv sync

# Playwright ブラウザのインストール
uv run playwright install chromium

# APIキーを設定
cp .env.example .env
# .env を編集して ANTHROPIC_API_KEY を設定

# 実行
uv run python company_research.py

#主な実装ポイント

項目                実装内容
Structured Output  llm.with_structured_output(CompanyInfo) で Pydantic モデルに変換
非同期処理          asyncio.run(main()) + 全処理を async/await
ブラウザ共有        Browser インスタンスを全社で使い回してコスト削減
エラー処理          例外をキャッチしてスキップ＋ログ出力、最後に失敗行も CSV に記録
CSV出力             utf-8-sig（BOM付き）でExcelで文字化けなし

デバッグ時は headless=False（デフォルト）でブラウザの動きを確認できます。本番運用では headless=True に変更してください（company_research.py:73）。


#Codespaces 対応の追加内容

#追加したファイル

.devcontainer/devcontainer.json — Codespaces 起動時に自動で uv sync と playwright install chromium を実行するよう設定しています。

#変更した点

company_research.py:76 — headless=True に変更（Codespaces はディスプレイなし環境のため）
README を Codespaces での手順に全面改訂
使う流れ
1.このフォルダを GitHub リポジトリに push
2.リポジトリの Settings → Secrets and variables → Codespaces に ANTHROPIC_API_KEY を登録
3.Code → Codespaces → Create codespace で起動（環境構築は自動）
4.ターミナルで uv run python company_research.py を実行
5.生成された output.csv を右クリック → Download

PC にインストールするものは何もなく、ブラウザだけで完結します。