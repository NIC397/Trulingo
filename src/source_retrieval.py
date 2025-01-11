import requests
from newspaper import Article
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

import argparse
import json
from pathlib import Path
import google.generativeai as genai
from googletrans import Translator

@dataclass
class ArticleInfo:
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    date: Optional[datetime] = None
    authors: Optional[List[str]] = None
    source: Optional[str] = None
    claim: Optional[str] = None
    language: Optional[str] = None

class SourceRetriever:
    def __init__(self, gemini_api_key: Optional[str] = None, google_api_key: Optional[str] = None, cse_id: Optional[str] = None):
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.translator = Translator()
        self.google_api_key = google_api_key
        self.cse_id = cse_id
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            self.model = None

        self.us_news_sources = ["CNN", "NYT", "Fox News"]
        self.cn_news_sources = ["凤凰网", "腾讯新闻", "环球网"]

    def search_articles_duckduckgo(self, query: str, news_sources: List[str], num_results: int = 5) -> List[str]:
        """Search for articles using DuckDuckGo with specific news sources."""
        results = []
        for source in news_sources:
            combined_query = f"{query} {source}"
            try:
                response = requests.get(
                    "https://duckduckgo.com/html/",
                    params={"q": combined_query},
                    headers=self.headers
                )
                print(response)
                soup = BeautifulSoup(response.content, "html.parser")
                for link in soup.find_all("a", {"class": "result__a"}, limit=num_results):
                    url = link["href"]
                    original_url = self._unwrap_duckduckgo_url(url)
                    if original_url:
                        results.append(original_url)
            except Exception as e:
                print(f"Error during search for {source}: {e}")
        return results

    def search_articles_google(self, query: str, news_sources: List[str], num_results: int = 5) -> List[str]:
        """Search for articles using Google Custom Search JSON API with specific news sources."""
        results = []
        if not self.google_api_key or not self.cse_id:
            print("Google API key or CSE ID not configured")
            return results

        for source in news_sources:
            combined_query = f"{query} {source}"
            try:
                response = requests.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": self.google_api_key,
                        "cx": self.cse_id,
                        "q": combined_query,
                        "num": num_results
                    }
                )
                print(f"Response status code for {source}: {response.status_code}")
                
                if response.status_code == 200:
                    search_results = response.json()
                    for item in search_results.get("items", []):
                        results.append(item["link"])
                elif response.status_code == 403:
                    print(f"Invalid API key or CSE ID for {source}.")
                else:
                    print(f"Unexpected status code {response.status_code} for {source}.")
            except Exception as e:
                print(f"Error during search for {source}: {e}")
        return results

    def _unwrap_duckduckgo_url(self, wrapped_url: str) -> Optional[str]:
        """Unwrap DuckDuckGo redirect URLs."""
        try:
            parsed_url = urlparse(wrapped_url)
            query_params = parse_qs(parsed_url.query)
            if "uddg" in query_params:
                return unquote(query_params["uddg"][0])
            return wrapped_url
        except Exception as e:
            print(f"Error unwrapping URL: {e}")
            return None

    def extract_article_info(self, url: str, claim: Optional[str] = None, language: Optional[str] = 'en') -> Optional[ArticleInfo]:
        """Extract information from an article."""
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            return ArticleInfo(
                url=url,
                title=article.title,
                content=article.text,
                date=article.publish_date,
                authors=article.authors,
                source=urlparse(url).netloc,
                claim=claim,
                language=language
            )
        except Exception as e:
            print(f"Error extracting content from {url}: {e}")
            return None

    def decompose_claim_with_gemini(self, claim: str):
        if not self.model:
            print("Gemini API key not configured")
            return None

        try:
            prompt = f"""
            You must respond with valid JSON only. We want to verify the given claim:
            
            Claim: {claim}

            To verify the claim we would need to search for articles and webpages that would contain 
            the necessary information to draw conclusions about the claim. Provide the minimum number of queries needed to have all the necessary information on hand.
            
            Respond with this exact JSON structure, no other text:
            {{
                "search_queries": ["<query>"]
            }}
            """

            response = self.model.generate_content(prompt)
            
            # Store raw response
            raw_response = response.text if response.parts else "No response generated"
            
            # Try to parse JSON response
            if response.parts:
                try:
                    result = json.loads(response.text)
                    return result, raw_response
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON. Raw response: {raw_response}")
                    return None, raw_response
            return None, raw_response
        except Exception as e:
            print(f"Error during claim verification: {e}")
            return None, str(e)

    def verify_claim_with_gemini(self, claim: str, context_en: str, context_zh: str) -> Optional[Dict[str, Any]]:
        """Verify a claim using Gemini API with provided English and Chinese contexts."""
        if not self.model:
            print("Gemini API key not configured")
            return None

        try:
            prompt = f"""
            You must respond with valid JSON only. Analyze this claim using the provided contexts:
            
            Claim: {claim}
            
            English Context:
            {context_en}
            
            Chinese Context:
            {context_zh}
            
            Respond with this exact JSON structure, no other text:
            {{
                "claim": "{claim}",
                "english_summary": "<summary of English context>",
                "chinese_summary": "<summary of Chinese context>",
                "comparison": "<comparison of English and Chinese contexts>",
                "conclusion": "<final conclusion based on both contexts>"
            }}
            """

            response = self.model.generate_content(prompt)
            
            # Store raw response
            raw_response = response.text if response.parts else "No response generated"
            
            # Try to parse JSON response
            if response.parts:
                try:
                    result = json.loads(response.text)
                    return result, raw_response
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON. Raw response: {raw_response}")
                    return None, raw_response
            return None, raw_response
        except Exception as e:
            print(f"Error during claim verification: {e}")
            return None, str(e)

    def search_and_process_articles(self, claim: str, selected_sources: Dict[str, bool], num_results: int = 5, verify: bool = False) -> pd.DataFrame:
        """Search and process articles relevant to a claim, optionally verify with Gemini."""
        claims = []
        if verify and self.model:
            output = self.decompose_claim_with_gemini(claim)
            if output[0] is not None:
                claims = output[0]["search_queries"]
            print("claims:", claims)

        print(f"Searching for articles relevant to the claim: {claim}")
        
        data = []
        context_en = ""
        context_zh = ""

        # Determine the language of the input claim
        detected_lang = self.translator.detect(claim).lang

        if detected_lang == 'en':
            claim_en = claim
            claim_zh = self.translator.translate(claim, src='en', dest='zh-cn').text
        else:
            claim_zh = claim
            claim_en = self.translator.translate(claim, src='zh-cn', dest='en').text

        if selected_sources.get('en'):
            # urls_en = self.search_articles_duckduckgo(claim_en, self.us_news_sources, num_results)
            urls_en = self.search_articles_google(claim_en, self.us_news_sources, num_results)
            for url in urls_en:
                print(f"Processing (EN): {url}")
                article_info = self.extract_article_info(url, claim, language='en')
                if article_info:
                    data.append(article_info.__dict__)
                    if verify and article_info.content:
                        context_en += article_info.content + "\n\n"

        if selected_sources.get('zh-cn'):
            # urls_zh = self.search_articles_duckduckgo(claim_zh, self.cn_news_sources, num_results)
            urls_zh = self.search_articles_google(claim_zh, self.cn_news_sources, num_results)
            for url in urls_zh:
                print(f"Processing (ZH): {url}")
                article_info = self.extract_article_info(url, claim, language='zh')
                if article_info:
                    data.append(article_info.__dict__)
                    if verify and article_info.content:
                        context_zh += article_info.content + "\n\n"

        results_df = pd.DataFrame(data)
        
        if verify and self.model:
            verification_result, raw_response = self.verify_claim_with_gemini(claim, context_en, context_zh)
            if verification_result:
                print("\nClaim Verification Result:")
                print(json.dumps(verification_result, indent=2))
                results_df.attrs['verification'] = verification_result
            results_df.attrs['raw_gemini_response'] = raw_response
        
        return results_df


def save_results(df: pd.DataFrame, output_path: str):
    """Save results to a file based on extension."""
    path = Path(output_path)
    if path.suffix == '.csv':
        df.to_csv(path, index=False)
    elif path.suffix == '.json':
        df.to_json(path, orient='records', date_format='iso')
    else:
        raise ValueError("Output file must be either .csv or .json")

def run_test():
    claims_to_test = [
    "MicroStrategy has benefited from the rally in cryptocurrencies this year", 
    "AI models are getting better almost every month right now", 
    r"Sales of iPhone were up less than 1% in fiscal 2024 (which ended in September)", 
    "The valuation of Circle’s shares on the private market reportedly reached $5 billion before Trump’s election",
    "Nvidia's projected earnings per share are expected to grow by 125.38% year-over-year in 2025.",
    "Higher-income households preferred online shopping during Thanksgiving weekend, while lower-income consumers favored in-person deals", 
    "The stock of Apple (NASDAQ: AAPL) is up 22% year to date in 2024", 
    "Nvidia's supply concerns, including delays with Blackwell AI chips, are reportedly resolved",
    "Amazon achieved record sales during Black Friday week in 2024, driven by early holiday discounts.",
    ]


def main():
    """Command line interface for source retrieval."""
    parser = argparse.ArgumentParser(description='Search and process articles for fact-checking.')
    parser.add_argument('claim', help='The claim to verify')
    parser.add_argument('-n', '--num-results', type=int, default=5,
                      help='Number of articles to retrieve per source (default: 5)')
    parser.add_argument('-o', '--output', help='Output file path (.csv or .json)')
    parser.add_argument('--verbose', action='store_true',
                      help='Print detailed processing information')
    parser.add_argument('--gemini-key', help='Gemini API key for claim verification')
    parser.add_argument('--verify', action='store_true',
                      help='Verify claim using Gemini API')
    parser.add_argument('--google-key', help='Google API key for article search')
    parser.add_argument('--cse-id', help='Google Custom Search Engine ID')

    args = parser.parse_args()
    
    retriever = SourceRetriever(gemini_api_key=args.gemini_key if args.verify else None, google_api_key=args.google_key, cse_id=args.cse_id)
    results_df = retriever.search_and_process_articles(
        args.claim, 
        {'en': True, 'zh': True},  # Default to both sources for CLI
        num_results=args.num_results,
        verify=args.verify
    )
    
    if args.verbose:
        print("\nResults found:")
        for idx, row in results_df.iterrows():
            print(f"\nSource {idx + 1}:")
            print(f"Title: {row['title']}")
            print(f"URL: {row['url']}")
            print(f"Date: {row['date']}")
            print(f"Source: {row['source']}")
            if row['authors']:
                print(f"Authors: {', '.join(row['authors'])}")
            print("-" * 50)

    if args.output:
        save_results(results_df, args.output)
        print(f"\nResults saved to: {args.output}")
    else:
        # Print a simple summary if no output file specified
        print("\nSummary:")
        for idx, row in results_df.iterrows():
            print(f"{idx + 1}. {row['title']} ({row['source']})")

    if args.verify and 'verification' in results_df.attrs:
        print("\nVerification Result:")
        print(json.dumps(results_df.attrs['verification'], indent=2))

if __name__ == "__main__":
    main()