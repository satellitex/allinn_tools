"""CLI entry point for AllInn Tools using Fire."""

import fire
from typing import Dict, Type

from .commands.shinkansen import ShinkansenCommand
from .core.base_command import BaseCommand


class AllInnCLI:
    """Main CLI class for AllInn Tools."""
    
    def __init__(self):
        self._commands: Dict[str, Type[BaseCommand]] = {
            'shinkansen': ShinkansenCommand,
        }
    
    def list_commands(self) -> None:
        """List all available commands."""
        print("Available commands:")
        for name, command_class in self._commands.items():
            cmd = command_class()
            print(f"  {name}: {cmd.description}")
    
    def shinkansen(self, 
                   output: str = 'shinkansen_population_density.csv',
                   route_filter: str = None,
                   sleep: float = 0.5,
                   api_key: str = None) -> str:
        """
        新幹線停車駅の人口・面積・人口密度CSVを生成（e-Stat API使用）
        
        Args:
            output: 出力CSVファイルパス
            route_filter: 対象路線をカンマ区切りで指定（例: '東海道,山陽'）
            sleep: リクエスト間隔（秒）
            api_key: e-Stat API キー（環境変数 ESTAT_API_KEY からも取得可能）
        
        Returns:
            出力ファイルパス
        """
        cmd = ShinkansenCommand()
        
        # route_filter をリストに変換
        route_list = None
        if route_filter:
            route_list = [r.strip() for r in route_filter.split(',')]
        
        return cmd.run(output=output, route_filter=route_list, sleep=sleep, api_key=api_key)


def main():
    """Main entry point for the CLI."""
    fire.Fire(AllInnCLI)