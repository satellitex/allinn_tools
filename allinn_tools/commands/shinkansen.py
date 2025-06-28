"""
新幹線停車駅 × 自治体人口密度 CSV ジェネレータ

Usage via CLI:
    allinn shinkansen --output shinkansen.csv --route-filter 東海道 山陽 --sleep 1.0
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote

import pandas as pd
import requests
from bs4 import BeautifulSoup

from ..core.base_command import BaseCommand


class PopulationDensityFetcher:
    """Wikipedia から人口密度データを取得するクラス"""
    
    def __init__(self, sleep_time: float = 0.5):
        self.sleep_time = sleep_time
        self.cache: Dict[str, Optional[float]] = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; AllInnTools/1.0)'
        })
    
    def extract_density(self, text: str) -> Optional[float]:
        """HTMLテキストから人口密度を抽出"""
        patterns = [
            r'(?:人口密度|Population density)[：:\s]*([0-9,]+(?:\.[0-9]+)?)\s*(?:人/km|/km²|per km)',
            r'density[：:\s]*([0-9,]+(?:\.[0-9]+)?)',
            r'([0-9,]+(?:\.[0-9]+)?)\s*(?:人/km²|/km²|per km²)',
            r'人口密度[：:\s]*([0-9,]+(?:\.[0-9]+)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    density_str = match.group(1).replace(',', '')
                    return float(density_str)
                except ValueError:
                    continue
        
        return None
    
    def fetch_wikipedia_page(self, municipality: str, prefecture: str) -> Optional[str]:
        """Wikipedia ページを取得"""
        queries = [
            f"{municipality}, {prefecture}",
            f"{municipality}",
            f"{municipality} {prefecture}"
        ]
        
        for query in queries:
            try:
                search_url = "https://en.wikipedia.org/w/api.php"
                search_params = {
                    'action': 'query',
                    'format': 'json',
                    'list': 'search',
                    'srsearch': query,
                    'srlimit': 3
                }
                
                response = self.session.get(search_url, params=search_params, timeout=10)
                response.raise_for_status()
                search_data = response.json()
                
                if 'query' in search_data and 'search' in search_data['query']:
                    for result in search_data['query']['search']:
                        page_title = result['title']
                        page_url = f"https://en.wikipedia.org/wiki/{quote(page_title)}"
                        page_response = self.session.get(page_url, timeout=10)
                        page_response.raise_for_status()
                        return page_response.text
                
                time.sleep(self.sleep_time)
                
            except Exception:
                continue
        
        return None
    
    def get_population_density(self, municipality: str, prefecture: str, logger) -> Optional[float]:
        """自治体の人口密度を取得"""
        cache_key = f"{municipality},{prefecture}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        logger.info(f"Fetching population density for {municipality}, {prefecture}")
        
        try:
            html_content = self.fetch_wikipedia_page(municipality, prefecture)
            if not html_content:
                logger.warning(f"No Wikipedia page found for {municipality}, {prefecture}")
                self.cache[cache_key] = None
                return None
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Infobox settlement を探す
            infobox = soup.find('table', class_='infobox')
            if infobox:
                density = self.extract_density(infobox.get_text())
                if density:
                    self.cache[cache_key] = density
                    logger.info(f"Found density for {municipality}: {density} people/km²")
                    return density
            
            # 全体のテキストから検索
            page_text = soup.get_text()
            density = self.extract_density(page_text)
            
            if density:
                self.cache[cache_key] = density
                logger.info(f"Found density for {municipality}: {density} people/km²")
                return density
            else:
                logger.warning(f"No population density found for {municipality}, {prefecture}")
                self.cache[cache_key] = None
                return None
                
        except Exception as e:
            logger.error(f"Error processing {municipality}, {prefecture}: {e}")
            self.cache[cache_key] = None
            return None
        
        finally:
            time.sleep(self.sleep_time)


class ShinkansenCommand(BaseCommand):
    """新幹線停車駅の人口密度CSV生成コマンド"""
    
    @property
    def name(self) -> str:
        return "shinkansen"
    
    @property
    def description(self) -> str:
        return "新幹線停車駅の人口密度CSVを生成"
    
    def _load_station_data(self) -> List[Dict]:
        """駅データをJSONファイルから読み込み"""
        json_path = Path(__file__).parent.parent.parent / "inputs" / "shinkansen" / "shinkansen_stations.json"
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading station data from {json_path}: {e}")
            raise
    
    def _filter_by_routes(self, data: List[Dict], route_filters: Optional[List[str]]) -> List[Dict]:
        """指定された路線でフィルタリング"""
        if not route_filters:
            return data
        
        filtered = []
        for station in data:
            for route_filter in route_filters:
                if route_filter.lower() in station['route'].lower():
                    filtered.append(station)
                    break
        
        return filtered
    
    def _create_csv(self, station_data: List[Dict], fetcher: PopulationDensityFetcher) -> pd.DataFrame:
        """CSV データを作成"""
        records = []
        
        for station in station_data:
            density = fetcher.get_population_density(
                station['municipality'], 
                station['prefecture'],
                self.logger
            )
            
            records.append({
                'route': station['route'],
                'station': station['station'],
                'municipality': station['municipality'],
                'prefecture': station['prefecture'],
                'population_density_km2': density
            })
        
        df = pd.DataFrame(records)
        
        # 路線別にランキングを付与
        df['rank_in_route'] = df.groupby('route')['population_density_km2'].rank(
            method='dense', 
            ascending=False,
            na_option='bottom'
        ).astype('Int64')
        
        # 路線内で人口密度順にソート
        df = df.sort_values(['route', 'population_density_km2'], ascending=[True, False])
        
        return df
    
    def run(self, 
            output: str = 'shinkansen_population_density.csv',
            route_filter: Optional[List[str]] = None,
            sleep: float = 0.5) -> str:
        """
        新幹線停車駅の人口密度CSVを生成
        
        Args:
            output: 出力CSVファイルパス
            route_filter: 対象路線を指定（例: ['東海道', '山陽']）
            sleep: リクエスト間隔（秒）
        
        Returns:
            出力ファイルパス
        """
        # 駅データを読み込み
        station_data = self._load_station_data()
        self.logger.info(f"Loaded {len(station_data)} stations")
        
        # 路線フィルタリング
        if route_filter:
            station_data = self._filter_by_routes(station_data, route_filter)
            self.logger.info(f"Filtered to {len(station_data)} stations for routes: {route_filter}")
        
        # 人口密度取得
        fetcher = PopulationDensityFetcher(sleep_time=sleep)
        
        # CSV作成
        self.logger.info("Starting data collection...")
        df = self._create_csv(station_data, fetcher)
        
        # CSV保存
        df.to_csv(output, index=False, encoding='utf-8')
        self.logger.info(f"CSV saved to {output}")
        
        # 統計情報
        total_stations = len(df)
        missing_density = df['population_density_km2'].isna().sum()
        missing_percentage = (missing_density / total_stations) * 100
        
        self.logger.info(f"Total stations: {total_stations}")
        self.logger.info(f"Missing density data: {missing_density} ({missing_percentage:.1f}%)")
        
        if missing_percentage > 1.0:
            self.logger.warning(f"Missing density data exceeds 1%: {missing_percentage:.1f}%")
        
        return output