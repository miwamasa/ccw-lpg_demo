"""
LPG Graph Builder

CSVデータを読み込み、Labeled Property Graphを構築します。
NetworkXを使用してグラフを表現します。
"""

import networkx as nx
import pandas as pd
from typing import Dict, List, Any
from pathlib import Path


class LPGBuilder:
    """
    CSVデータからLabeled Property Graphを構築するクラス
    
    Attributes:
        graph (nx.MultiDiGraph): 構築されたグラフ
    """
    
    def __init__(self):
        """MultiDiGraphを初期化（複数エッジ、有向グラフ対応）"""
        self.graph = nx.MultiDiGraph()
    
    def load_facilities(self, csv_path: str) -> None:
        """
        施設マスタデータを読み込み、Facilityノードを作成
        
        Args:
            csv_path: CSVファイルのパス
        """
        df = pd.read_csv(csv_path)
        
        for _, row in df.iterrows():
            facility_id = row['facility_id']
            
            # ノードを追加（ラベル: Facility）
            self.graph.add_node(
                facility_id,
                label='Facility',
                name=row['facility_name'],
                facility_type=row['facility_type'],
                location=row['location'],
                capacity=row['capacity']
            )
            
        print(f"✓ 施設ノードを{len(df)}件追加しました")
    
    def load_emissions(self, csv_path: str) -> None:
        """
        排出量データを読み込み、EmissionRecordノードと関係を作成
        
        Args:
            csv_path: CSVファイルのパス
        """
        df = pd.read_csv(csv_path)
        
        for idx, row in df.iterrows():
            # 排出記録ノードのID
            record_id = f"EMI_{row['facility_id']}_{row['year']}{row['month']:02d}"
            
            # 排出記録ノードを追加
            self.graph.add_node(
                record_id,
                label='EmissionRecord',
                year=row['year'],
                month=row['month'],
                co2_emissions_kg=row['co2_emissions_kg'],
                waste_kg=row['waste_kg'],
                water_usage_m3=row['water_usage_m3']
            )
            
            # 施設 → 排出記録 の関係を作成
            self.graph.add_edge(
                row['facility_id'],
                record_id,
                label='HAS_EMISSION',
                year=row['year'],
                month=row['month']
            )
        
        print(f"✓ 排出記録ノードを{len(df)}件追加しました")
    
    def load_energy(self, csv_path: str) -> None:
        """
        エネルギー使用データを読み込み、EnergyRecordノードと関係を作成
        
        Args:
            csv_path: CSVファイルのパス
        """
        df = pd.read_csv(csv_path)
        
        for idx, row in df.iterrows():
            # エネルギー記録ノードのID
            record_id = f"ENE_{row['facility_id']}_{row['year']}{row['month']:02d}"
            
            # エネルギー記録ノードを追加
            self.graph.add_node(
                record_id,
                label='EnergyRecord',
                year=row['year'],
                month=row['month'],
                electricity_kwh=row['electricity_kwh'],
                gas_m3=row['gas_m3'],
                renewable_ratio=row['renewable_ratio']
            )
            
            # 施設 → エネルギー記録 の関係を作成
            self.graph.add_edge(
                row['facility_id'],
                record_id,
                label='HAS_ENERGY',
                year=row['year'],
                month=row['month']
            )
        
        print(f"✓ エネルギー記録ノードを{len(df)}件追加しました")
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """
        グラフの統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        node_labels = {}
        for node, data in self.graph.nodes(data=True):
            label = data.get('label', 'Unknown')
            node_labels[label] = node_labels.get(label, 0) + 1
        
        edge_labels = {}
        for u, v, key, data in self.graph.edges(data=True, keys=True):
            label = data.get('label', 'Unknown')
            edge_labels[label] = edge_labels.get(label, 0) + 1
        
        return {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'node_types': node_labels,
            'edge_types': edge_labels
        }


if __name__ == '__main__':
    # デモ実行
    builder = LPGBuilder()
    
    data_dir = Path(__file__).parent.parent / 'data'
    
    builder.load_facilities(data_dir / 'facilities.csv')
    builder.load_emissions(data_dir / 'emissions.csv')
    builder.load_energy(data_dir / 'energy.csv')
    
    stats = builder.get_graph_stats()
    print("\n=== グラフ統計 ===")
    print(f"ノード総数: {stats['total_nodes']}")
    print(f"エッジ総数: {stats['total_edges']}")
    print(f"ノードタイプ: {stats['node_types']}")
    print(f"エッジタイプ: {stats['edge_types']}")
