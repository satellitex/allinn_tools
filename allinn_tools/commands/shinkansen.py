"""
新幹線停車駅 × 自治体人口密度 CSV ジェネレータ (e-Stat API版)

Usage via CLI:
    allinn shinkansen --output shinkansen.csv --route-filter 東海道 山陽 --sleep 1.0 --api-key YOUR_API_KEY
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os

import pandas as pd
import requests
from dotenv import load_dotenv

from ..core.base_command import BaseCommand

# .env ファイルを読み込み
load_dotenv()


class EStatAPIClient:
    """e-Stat API を使用して統計データを取得するクライアント"""
    
    def __init__(self, api_key: str, sleep_time: float = 0.5):
        self.api_key = api_key
        self.sleep_time = sleep_time
        self.cache: Dict[str, Optional[Tuple[float, float, float]]] = {}
        self.all_data_cache: Optional[Dict[str, Dict[str, float]]] = None  # 全国データキャッシュ
        self.base_url = "https://api.e-stat.go.jp/rest/3.0/app/json"
        
        # SSDS 基礎データ（社会・人口統計体系 市区町村データ）
        self.population_stats_id = "0000020201"  # 人口データ
        self.area_stats_id = "0000020102"        # 面積データ
        self.population_indicator = "A1101"      # 総人口（人）
        self.area_indicator = "B1101"            # 総面積（km²）
        self.time_code = "2020100000"  # 2020年データ（最新利用可能）
        
    def _get_municipality_code(self, municipality: str, _: str) -> Optional[str]:
        """自治体名から統計コードを取得"""
        # 簡易的なマッピング（実際にはより包括的な辞書が必要）
        municipality_codes = {
            # 東京都特別区
            "千代田区": "13101",
            "台東区": "13106",
            "港区": "13103",
            
            # 政令指定都市（例）
            "横浜市": "14100",
            "大阪市": "27100",
            "名古屋市": "23100",
            "京都市": "26100",
            "神戸市": "28100",
            "福岡市": "40130",
            "さいたま市": "11100",
            "仙台市": "04100",
            "広島市": "34100",
            "北九州市": "40100",
            
            # その他の市町村（一部例）
            "小田原市": "14205",
            "熱海市": "22205",
            "三島市": "22206",
            "富士市": "22210",
            "静岡市": "22100",
            "掛川市": "22213",
            "浜松市": "22130",
            "豊橋市": "23201",
            "安城市": "23212",
            "羽島市": "21207",
            "米原市": "25213",
            "明石市": "28204",
            "姫路市": "28201",
            "相生市": "28202",
            "岡山市": "33100",
            "倉敷市": "33202",
            "福山市": "34207",
            "尾道市": "34205",
            "三原市": "34204",
            "東広島市": "34212",
            "岩国市": "35203",
            "周南市": "35216",
            "山口市": "35201",
            "山陽小野田市": "35220",
            "下関市": "35201",
            "鳥栖市": "41205",
            "久留米市": "40203",
            "筑後市": "40210",
            "大牟田市": "40202",
            "玉名市": "43206",
            "熊本市": "43100",
            "八代市": "43202",
            "水俣市": "43205",
            "出水市": "46203",
            "薩摩川内市": "46215",
            "鹿児島市": "46201",
            
            # 北海道・東北
            "青森市": "02201",
            "八戸市": "02203",
            "盛岡市": "03201",
            "仙台市": "04100",
            "秋田市": "05201",
            "山形市": "06201",
            "福島市": "07201",
            "郡山市": "07203",
            "白河市": "07205",
            
            # 関東
            "宇都宮市": "09201",
            "小山市": "09203",
            "那須塩原市": "09213",
            "熊谷市": "11202",
            "本庄市": "11206",
            "高崎市": "10202",
            "安中市": "10206",
            "新潟市": "15100",
            "長岡市": "15202",
            "三条市": "15204",
            "南魚沼市": "15226",
            "上越市": "15222",
            "糸魚川市": "15216",
            
            # 中部・北陸
            "長野市": "20201",
            "上田市": "20203",
            "佐久市": "20217",
            "飯山市": "20212",
            "富山市": "16201",
            "高岡市": "16202",
            "黒部市": "16205",
            "金沢市": "17201",
            
            # 町村の例
            "湯沢町": "15482",
            "みなかみ町": "10449",
            "軽井沢町": "20321",
            "今別町": "02323",
            "木古内町": "01334",
            "北斗市": "01234",
            "高畠町": "06382",
            "南陽市": "06212",
            "上山市": "06204",
            "天童市": "06205",
            "東根市": "06207",
            "村山市": "06208",
            "新庄市": "06210",
            "大石田町": "06428",
            "米沢市": "06202",
            "雫石町": "03366",
            "仙北市": "05215",
            "大仙市": "05213",
            "一関市": "03209",
            "奥州市": "03215",
            "北上市": "03205",
            "花巻市": "03203",
            "岩手町": "03367",
            "二戸市": "03207",
            "七戸町": "02403",
            "白石市": "04205",
            "大崎市": "04215",
            "栗原市": "04213"
        }
        
        return municipality_codes.get(municipality)
    
    def _fetch_all_data(self, logger) -> bool:
        """全国の統計データを一度に取得してキャッシュ"""
        if self.all_data_cache is not None:
            return True
            
        logger.info("Fetching all municipality data from e-Stat API...")
        
        try:
            # 人口データを取得
            logger.debug("Fetching population data...")
            population_params = {
                "appId": self.api_key,
                "statsDataId": self.population_stats_id,
                "cdCat01": self.population_indicator,
                "cdTime": self.time_code,
                "limit": 100000
            }
            
            population_response = requests.get(f"{self.base_url}/getStatsData", params=population_params, timeout=30)
            population_response.raise_for_status()
            population_data = population_response.json()
            
            # 面積データを取得
            logger.debug("Fetching area data...")
            area_params = {
                "appId": self.api_key,
                "statsDataId": self.area_stats_id,
                "cdCat01": self.area_indicator,
                "cdTime": self.time_code,
                "limit": 100000
            }
            
            area_response = requests.get(f"{self.base_url}/getStatsData", params=area_params, timeout=30)
            area_response.raise_for_status()
            area_data = area_response.json()
            
            # データを整理
            self.all_data_cache = {}
            
            # 人口データを処理
            pop_stats_data = population_data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
            for item in pop_stats_data:
                if not isinstance(item, dict):
                    continue
                
                area_code = item.get("@area")
                value_str = item.get("$", "")
                
                if not area_code:
                    continue
                
                try:
                    value = float(value_str) if value_str and value_str != "-" and value_str.strip() else None
                except (ValueError, TypeError):
                    value = None
                
                if area_code not in self.all_data_cache:
                    self.all_data_cache[area_code] = {}
                
                if value is not None:
                    self.all_data_cache[area_code]["A1101"] = value
            
            # 面積データを処理
            area_stats_data = area_data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
            for item in area_stats_data:
                if not isinstance(item, dict):
                    continue
                
                area_code = item.get("@area")
                value_str = item.get("$", "")
                
                if not area_code:
                    continue
                
                try:
                    value = float(value_str) if value_str and value_str != "-" and value_str.strip() else None
                except (ValueError, TypeError):
                    value = None
                
                if area_code not in self.all_data_cache:
                    self.all_data_cache[area_code] = {}
                
                if value is not None:
                    self.all_data_cache[area_code]["B1101"] = value
            
            logger.info(f"Cached data for {len(self.all_data_cache)} municipalities")
            
            # デバッグ: いくつかのサンプルデータを表示
            if self.all_data_cache:
                sample_code = list(self.all_data_cache.keys())[0]
                sample_data = self.all_data_cache[sample_code]
                logger.debug(f"Sample data for {sample_code}: {sample_data}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error fetching all data from e-Stat API: {e}")
            return False
    
    def get_population_data(self, municipality: str, prefecture: str, logger) -> Optional[Tuple[float, float, float]]:
        """自治体の人口、面積、人口密度を取得"""
        cache_key = f"{municipality},{prefecture}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 全国データが未取得の場合は取得
        if not self._fetch_all_data(logger):
            logger.error("Failed to fetch all data from e-Stat API")
            self.cache[cache_key] = None
            return None
        
        municipality_code = self._get_municipality_code(municipality, prefecture)
        if not municipality_code:
            logger.warning(f"Municipality code not found for {municipality}, {prefecture}")
            self.cache[cache_key] = None
            return None
        
        # 市区町村コードはそのまま使用（APIデータは5桁形式）
        area_code = municipality_code
        
        logger.debug(f"Looking for data for {municipality} with area code: {area_code}")
        
        
        # キャッシュからデータを取得
        if area_code not in self.all_data_cache:
            logger.warning(f"No data found for {municipality} (area code: {area_code}) in cached data")
            self.cache[cache_key] = None
            return None
        
        area_data = self.all_data_cache[area_code]
        
        population = area_data.get("A1101")
        area = area_data.get("B1101")
        
        # 人口密度を計算
        density = None
        if population is not None and area is not None and area > 0:
            density = population / area
            logger.debug(f"Calculated density for {municipality}: {density}")
        
        # 最低限人口データがあれば成功とする
        if population is not None:
            result = (population, area, density)
            self.cache[cache_key] = result
            area_str = f"{area:.2f}km²" if area else "N/A"
            density_str = f"{density:.1f}people/km²" if density else "N/A"
            logger.info(f"Found data for {municipality}: population={population:,.0f}, area={area_str}, density={density_str}")
            return result
        
        logger.warning(f"Could not extract population data for {municipality}, {prefecture}")
        self.cache[cache_key] = None
        return None
    


class ShinkansenCommand(BaseCommand):
    """新幹線停車駅の人口密度CSV生成コマンド（e-Stat API版）"""
    
    @property
    def name(self) -> str:
        return "shinkansen"
    
    @property
    def description(self) -> str:
        return "新幹線停車駅の人口・面積・人口密度CSVを生成（e-Stat API使用）"
    
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
    
    def _create_csv(self, station_data: List[Dict], client: EStatAPIClient) -> pd.DataFrame:
        """CSV データを作成"""
        records = []
        
        for station in station_data:
            data = client.get_population_data(
                station['municipality'], 
                station['prefecture'],
                self.logger
            )
            
            population = None
            area = None
            density = None
            
            if data:
                population, area, density = data
            
            records.append({
                'route': station['route'],
                'station': station['station'],
                'municipality': station['municipality'],
                'prefecture': station['prefecture'],
                'population': population,
                'area_km2': area,
                'population_density_km2': density
            })
        
        df = pd.DataFrame(records)
        
        # 路線別にランキングを付与（人口密度ベース）
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
            sleep: float = 0.5,
            api_key: Optional[str] = None) -> str:
        """
        新幹線停車駅の人口・面積・人口密度CSVを生成
        
        Args:
            output: 出力CSVファイルパス
            route_filter: 対象路線を指定（例: ['東海道', '山陽']）
            sleep: リクエスト間隔（秒）
            api_key: e-Stat API キー（環境変数 ESTAT_API_KEY からも取得可能）
        
        Returns:
            出力ファイルパス
        """
        # API キーの取得
        if not api_key:
            api_key = os.getenv('ESTAT_API_KEY')
        
        if not api_key:
            raise ValueError(
                "e-Stat API key is required. "
                "Provide it via --api_key parameter or ESTAT_API_KEY environment variable. "
                "Get your API key from: https://www.e-stat.go.jp/api/"
            )
        
        # 駅データを読み込み
        station_data = self._load_station_data()
        self.logger.info(f"Loaded {len(station_data)} stations")
        
        # 路線フィルタリング
        if route_filter:
            station_data = self._filter_by_routes(station_data, route_filter)
            self.logger.info(f"Filtered to {len(station_data)} stations for routes: {route_filter}")
        
        # e-Stat API クライアント作成
        client = EStatAPIClient(api_key=api_key, sleep_time=sleep)
        
        # CSV作成
        self.logger.info("Starting data collection from e-Stat API...")
        df = self._create_csv(station_data, client)
        
        # CSV保存
        df.to_csv(output, index=False, encoding='utf-8')
        self.logger.info(f"CSV saved to {output}")
        
        # 統計情報
        total_stations = len(df)
        missing_population = df['population'].isna().sum()
        missing_area = df['area_km2'].isna().sum()
        missing_density = df['population_density_km2'].isna().sum()
        
        missing_percentage = (missing_density / total_stations) * 100
        
        self.logger.info(f"Total stations: {total_stations}")
        self.logger.info(f"Missing population data: {missing_population}")
        self.logger.info(f"Missing area data: {missing_area}")
        self.logger.info(f"Missing density data: {missing_density} ({missing_percentage:.1f}%)")
        
        if missing_percentage > 1.0:
            self.logger.warning(f"Missing density data exceeds 1%: {missing_percentage:.1f}%")
        
        return output