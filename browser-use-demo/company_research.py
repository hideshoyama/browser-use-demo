"""
企業情報自動収集スクリプト
browser-use + Ollama（qwen2.5:3b）を使って企業の公式サイトから情報を収集する
companies.txt に「企業名,公式URL」の形式で記載することでGoogle検索を回避する
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
CSV_HEADERS = ["会社名", "代表者名", "所在地", "事業内容", "公式サイトURL", "入力企業名", "ステータス"]


# --- 入力ファイル読み込み ---

def load_companies() -> list[tuple[str, str]]:
    """companies.txt を読み込み (企業名, URL) のリストを返す"""
    companies = []
    for line in INPUT_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(",", 1)
        if len(parts) != 2:
            logger.warning(f"形式エラー（スキップ）: {line}  ※ 「企業名,URL」の形式で記載してください")
            continue
        companies.append((parts[0].strip(), parts[1].strip()))
    return companies


# --- エージェントタスク ---

def build_task(company_name: str, url: str) -> str:
    return f"""
以下の手順で「{company_name}」の企業情報を収集してください。

1. 次の公式サイトURLに直接アクセスする:
   {url}
2. トップページを確認した後、「会社概要」「企業情報」「About Us」などのリンクを探してクリックする
3. 以下の情報を収集して返す:
   - 会社名（正式名称）
   - 代表者名（役職と氏名。例: 代表取締役社長 山田 太郎）
   - 本社所在地（都道府県・市区町村レベルまで）
   - 事業内容（100文字以内）
   - 公式サイトURL（アクセスしたURL）

情報が見つからない項目は「不明」とすること。
"""


# --- メイン処理 ---

async def research_company(
    company_name: str,
    url: str,
    llm: ChatOllama,
    browser: Browser,
) -> Optional[CompanyInfo]:
    """1社分の企業情報を収集する"""
    task = build_task(company_name, url)

    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        use_vision=False,  # CPU負荷軽減のためvision無効
    )

    try:
        result = await agent.run(max_steps=10)

        final_output = result.final_result()
        if not final_output:
            logger.warning(f"[{company_name}] エージェントが結果を返しませんでした")
            return None

        llm_structured = llm.with_structured_output(CompanyInfo)
        info: CompanyInfo = await llm_structured.ainvoke(
            f"以下のテキストから企業情報を構造化して抽出してください:\n\n{final_output}"
        )
        return info

    except Exception as e:
        logger.error(f"[{company_name}] エラー: {e}")
        return None


async def main() -> None:
    if not INPUT_FILE.exists():
        logger.error(f"{INPUT_FILE} が見つかりません")
        sys.exit(1)

    companies = load_companies()
    if not companies:
        logger.error("companies.txt に有効な企業情報がありません")
        sys.exit(1)

    logger.info(f"{len(companies)} 社の情報収集を開始します")

    llm = ChatOllama(
        model="qwen2.5:3b",
        temperature=0.0,
    )

    browser = Browser(
        config=BrowserConfig(
            headless=True,
        )
    )

    results: list[dict] = []

    try:
        for company_name, url in companies:
            logger.info(f"処理中: {company_name} ({url})")
            info = await research_company(company_name, url, llm, browser)

            if info:
                results.append({
                    "会社名": info.company_name,
                    "代表者名": info.representative,
                    "所在地": info.address,
                    "事業内容": info.business,
                    "公式サイトURL": info.website_url,
                    "入力企業名": company_name,
                    "ステータス": "成功",
                })
                logger.info(f"[{company_name}] 完了")
            else:
                results.append({
                    "会社名": company_name,
                    "代表者名": "",
                    "所在地": "",
                    "事業内容": "",
                    "公式サイトURL": url,
                    "入力企業名": company_name,
                    "ステータス": "失敗",
                })
                logger.warning(f"[{company_name}] スキップ（情報取得失敗）")

    finally:
        await browser.close()

    with OUTPUT_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(results)

    success = sum(1 for r in results if r["ステータス"] == "成功")
    logger.info(f"完了: {success}/{len(companies)} 社成功 → {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
