# browser-use-demo

browser-use + Anthropic Claude を使って企業の公式サイトから情報を自動収集するスクリプトです。
**GitHub Codespaces** で動かすことを前提にしています。

## Codespaces での起動方法

### 1. このリポジトリを GitHub に push する

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/<your-name>/<repo-name>.git
git push -u origin main
```

### 2. API キーを Codespaces Secrets に登録する

GitHub リポジトリの **Settings → Secrets and variables → Codespaces** から
`ANTHROPIC_API_KEY` を追加する。

### 3. Codespaces を起動する

リポジトリページの **Code → Codespaces → Create codespace on main**

起動時に自動で以下が実行されます（`devcontainer.json` の設定）:
- uv のインストール
- `uv sync` で依存関係インストール
- `playwright install chromium --with-deps` でブラウザインストール

### 4. 企業名を編集して実行

```bash
# companies.txt を編集
nano companies.txt

# 実行
uv run python company_research.py
```

### 5. output.csv をダウンロード

Codespaces のファイルエクスプローラーで `output.csv` を右クリック → **Download**

---

## 出力形式

| 列名 | 内容 |
|------|------|
| 会社名 | 正式名称 |
| 代表者名 | 役職と氏名 |
| 所在地 | 本社所在地 |
| 事業内容 | 100文字以内 |
| 公式サイトURL | 公式サイトのURL |
| 検索キーワード | companies.txt に記載の企業名 |
| ステータス | 成功 / 失敗 |

## 設定変更

`company_research.py` 内の主な設定:

| 設定 | デフォルト | 説明 |
|------|-----------|------|
| `headless` | `True` | Codespaces はディスプレイなしのため True 固定推奨 |
| `max_steps` | `15` | エージェントの最大ステップ数（増やすと精度↑・時間↑） |
| `model` | `claude-opus-4-6` | 使用する Claude モデル |

## ローカルで動かしたい場合

```bash
cp .env.example .env
# .env に ANTHROPIC_API_KEY を記載

uv sync
uv run playwright install chromium
uv run python company_research.py
```

ブラウザを表示したい場合は `headless = True` → `False` に変更してください。
