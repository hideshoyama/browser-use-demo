"""
企業情報自動収集スクリプト
browser-use + Ollama（qwen2.5:7b）を使って企業の公式サイトから情報を収集する
"""

import asyncio
import csv
import logging
import sys
from pathlib import Path
from typing import Optional

from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field
from browser_use import Agent, Browser, BrowserConfig

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# --- Structured Output モデル ---

class CompanyInfo(BaseModel):
    company_name: str = Field(description="会社名（正式名称）")
    representative: str = Field(description="代表者名（役職と氏名）。不明な場合は '不明'")
    address: str = Field(description="本社所在地（都道府県・市区町村レベルまで）。不明な場合は '不明'")
    business: str = Field(description="事業内容（100文字以内で簡潔に）")
    website_url: str = Field(description="公式サイトのURL")


# --- 定数 ---

INPUT_FILE = Path("companies.txt")
OUTPUT_FILE = Path("output.csv")
CSV_HEADERS = ["会社名", "代表者名", "所在地", "事業内容", "公式サイトURL", "検索キーワード", "ステータス"]


# --- エージェントタスク ---

def build_task(company_name: str) -> str:
    return f"""
以下の手順で「{company_name}」の企業情報を収集してください。

1. Google（https://www.google.com）で「{company_name} 公式サイト」を検索する
2. 検索結果から公式サイト（企業の公式ドメイン）にアクセスする
   - wikipedia、転職サイト、ニュースサイトなどは除外すること
3. 公式サイト内の「会社概要」「企業情報」「About Us」などのページも確認する
4. 以下の情報を取得して返す:
   - 会社名（正式名称）
   - 代表者名（役職と氏名。例: 代表取締役社長 山田 太郎）
   - 本社所在地（都道府県・市区町村レベルまで）
   - 事業内容（100文字以内）
   - 公式サイトURL

情報が見つからない項目は「不明」とすること。
"""


# --- メイン処理 ---

async def research_company(
    company_name: str,
    llm: ChatOllama,
    browser: Browser,
) -> Optional[CompanyInfo]:
    """1社分の企業情報を収集する"""
    task = build_task(company_name)

    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        use_vision=True,
    )

    try:
        result = await agent.run(max_steps=15)

        # AgentHistoryList から最終出力を取得
        final_output = result.final_result()
        if not final_output:
            logger.warning(f"[{company_name}] エージェントが結果を返しませんでした")
            return None

        # structured output として parse
        llm_structured = llm.with_structured_output(CompanyInfo)
        info: CompanyInfo = await llm_structured.ainvoke(
            f"以下のテキストから企業情報を構造化して抽出してください:\n\n{final_output}"
        )
        return info

    except Exception as e:
        logger.error(f"[{company_name}] エラー: {e}")
        return None


async def main() -> None:
    # 入力ファイル確認
    if not INPUT_FILE.exists():
        logger.error(f"{INPUT_FILE} が見つかりません")
        sys.exit(1)

    companies = [
        line.strip()
        for line in INPUT_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not companies:
        logger.error("companies.txt に企業名がありません")
        sys.exit(1)

    logger.info(f"{len(companies)} 社の情報収集を開始します")

    # LLM 初期化（Ollama）
    # function calling 対応モデルを使用
    # 他の選択肢: llama3.1:8b, mistral-nemo
    llm = ChatOllama(
        model="qwen2.5:3b",
        temperature=0.0,
    )

    # ブラウザ初期化（1インスタンスを使い回す）
    # Codespaces / CI 環境ではディスプレイがないため headless=True
    # ローカルでブラウザの動きを確認したい場合は False に変更
    headless = True
    browser = Browser(
        config=BrowserConfig(
            headless=headless,
        )
    )

    results: list[dict] = []

    try:
        for company_name in companies:
            logger.info(f"処理中: {company_name}")
            info = await research_company(company_name, llm, browser)

            if info:
                results.append({
                    "会社名": info.company_name,
                    "代表者名": info.representative,
                    "所在地": info.address,
                    "事業内容": info.business,
                    "公式サイトURL": info.website_url,
                    "検索キーワード": company_name,
                    "ステータス": "成功",
                })
                logger.info(f"[{company_name}] 完了: {info.website_url}")
            else:
                results.append({
                    "会社名": company_name,
                    "代表者名": "",
                    "所在地": "",
                    "事業内容": "",
                    "公式サイトURL": "",
                    "検索キーワード": company_name,
                    "ステータス": "失敗",
                })
                logger.warning(f"[{company_name}] スキップ（情報取得失敗）")

    finally:
        await browser.close()

    # CSV 出力（BOM付きUTF-8）
    with OUTPUT_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(results)

    success = sum(1 for r in results if r["ステータス"] == "成功")
    logger.info(f"完了: {success}/{len(companies)} 社成功 → {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
