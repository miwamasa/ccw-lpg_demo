"""
Knowledge Transformation Module

既存のLPGに新しい関係性やマッピングを導入し、
知識の変換・合成を行います。これがLPGの柔軟性の核心です。
"""

import networkx as nx
from typing import Dict, List, Tuple, Any
from datetime import datetime


class KnowledgeTransformer:
    """
    LPGに対して知識変換と合成を行うクラス
    
    LPGの柔軟性:
    1. 既存のグラフ構造を変更せずに新しい関係を追加
    2. データを横断的に結合して新しい知見を生成
    3. メタレベルの情報を動的に付与
    """
    
    def __init__(self, graph: nx.MultiDiGraph):
        """
        Args:
            graph: 変換対象のLPG
        """
        self.graph = graph
        self.transformations = []
    
    def link_emission_and_energy(self) -> None:
        """
        【変換1】排出記録とエネルギー記録を結びつける
        
        同じ施設・同じ期間のデータを横断的にリンク。
        これにより、CO2排出量とエネルギー使用量の関係を分析可能に。
        """
        emission_nodes = [n for n, d in self.graph.nodes(data=True) 
                         if d.get('label') == 'EmissionRecord']
        energy_nodes = [n for n, d in self.graph.nodes(data=True)
                       if d.get('label') == 'EnergyRecord']
        
        links_added = 0
        for emi_node in emission_nodes:
            emi_data = self.graph.nodes[emi_node]
            
            for ene_node in energy_nodes:
                ene_data = self.graph.nodes[ene_node]
                
                # 同じ施設・同じ期間をマッチング
                if (emi_node.split('_')[1] == ene_node.split('_')[1] and
                    emi_data['year'] == ene_data['year'] and
                    emi_data['month'] == ene_data['month']):
                    
                    # 新しい関係: CORRELATES_WITH を追加
                    self.graph.add_edge(
                        emi_node,
                        ene_node,
                        label='CORRELATES_WITH',
                        relation_type='temporal_match',
                        created_by='transformer'
                    )
                    links_added += 1
        
        self.transformations.append({
            'type': 'cross_linking',
            'description': '排出記録とエネルギー記録の相関リンク',
            'count': links_added
        })
        print(f"✓ 相関リンクを{links_added}件追加しました")
    
    def calculate_intensity_metrics(self) -> None:
        """
        【変換2】原単位メトリクスを計算して新ノード作成
        
        既存データから派生した知識（CO2排出原単位など）を
        新しいノードとして追加。これにより効率性の評価が可能に。
        """
        facilities = [n for n, d in self.graph.nodes(data=True)
                     if d.get('label') == 'Facility']
        
        intensity_nodes = 0
        for facility in facilities:
            facility_data = self.graph.nodes[facility]
            
            # この施設の排出記録を取得
            emission_records = [n for n in self.graph.successors(facility)
                               if self.graph.nodes[n].get('label') == 'EmissionRecord']
            
            # この施設のエネルギー記録を取得
            energy_records = [n for n in self.graph.successors(facility)
                             if self.graph.nodes[n].get('label') == 'EnergyRecord']
            
            # 各月の原単位を計算
            for emi_rec in emission_records:
                emi_data = self.graph.nodes[emi_rec]
                
                # 対応するエネルギー記録を検索
                matching_ene = None
                for ene_rec in energy_records:
                    ene_data = self.graph.nodes[ene_rec]
                    if (ene_data['year'] == emi_data['year'] and
                        ene_data['month'] == emi_data['month']):
                        matching_ene = ene_rec
                        break
                
                if matching_ene:
                    ene_data = self.graph.nodes[matching_ene]
                    
                    # 原単位ノードを作成
                    intensity_id = f"INT_{facility}_{emi_data['year']}{emi_data['month']:02d}"
                    
                    # CO2排出原単位 (kg-CO2/kWh)
                    co2_intensity = (emi_data['co2_emissions_kg'] / 
                                    ene_data['electricity_kwh'] 
                                    if ene_data['electricity_kwh'] > 0 else 0)
                    
                    # 水使用原単位 (m3/kWh)
                    water_intensity = (emi_data['water_usage_m3'] / 
                                      ene_data['electricity_kwh']
                                      if ene_data['electricity_kwh'] > 0 else 0)
                    
                    self.graph.add_node(
                        intensity_id,
                        label='IntensityMetrics',
                        year=emi_data['year'],
                        month=emi_data['month'],
                        co2_intensity_kg_per_kwh=round(co2_intensity, 4),
                        water_intensity_m3_per_kwh=round(water_intensity, 6),
                        renewable_ratio=ene_data['renewable_ratio'],
                        derived_from='emission_and_energy'
                    )
                    
                    # 関係を追加
                    self.graph.add_edge(facility, intensity_id, 
                                       label='HAS_INTENSITY',
                                       computed=True)
                    self.graph.add_edge(intensity_id, emi_rec,
                                       label='DERIVED_FROM_EMISSION')
                    self.graph.add_edge(intensity_id, matching_ene,
                                       label='DERIVED_FROM_ENERGY')
                    
                    intensity_nodes += 1
        
        self.transformations.append({
            'type': 'metric_derivation',
            'description': '原単位メトリクスノードの生成',
            'count': intensity_nodes
        })
        print(f"✓ 原単位メトリクスノードを{intensity_nodes}件追加しました")
    
    def classify_performance(self) -> None:
        """
        【変換3】パフォーマンス評価ラベルを付与
        
        原単位に基づいて施設を分類。
        メタ情報を動的に追加することで、レポート生成が容易に。
        """
        intensity_nodes = [n for n, d in self.graph.nodes(data=True)
                          if d.get('label') == 'IntensityMetrics']
        
        # 全体の平均CO2原単位を計算
        co2_intensities = [self.graph.nodes[n]['co2_intensity_kg_per_kwh']
                          for n in intensity_nodes]
        avg_co2_intensity = sum(co2_intensities) / len(co2_intensities) if co2_intensities else 0
        
        classifications = 0
        for node in intensity_nodes:
            node_data = self.graph.nodes[node]
            co2_int = node_data['co2_intensity_kg_per_kwh']
            renewable = node_data['renewable_ratio']
            
            # パフォーマンス分類
            if co2_int < avg_co2_intensity * 0.8 and renewable > 0.25:
                performance = 'Excellent'
            elif co2_int < avg_co2_intensity and renewable > 0.15:
                performance = 'Good'
            elif co2_int < avg_co2_intensity * 1.2:
                performance = 'Average'
            else:
                performance = 'NeedsImprovement'
            
            # 動的にプロパティを追加（LPGの柔軟性！）
            self.graph.nodes[node]['performance_rating'] = performance
            self.graph.nodes[node]['avg_benchmark'] = round(avg_co2_intensity, 4)
            self.graph.nodes[node]['rating_timestamp'] = datetime.now().isoformat()
            
            classifications += 1
        
        self.transformations.append({
            'type': 'classification',
            'description': 'パフォーマンス評価の付与',
            'count': classifications
        })
        print(f"✓ パフォーマンス評価を{classifications}件付与しました")
    
    def create_aggregation_nodes(self) -> None:
        """
        【変換4】集約ノードの作成
        
        施設ごとの月次データを集約して、レポート用の統計ノードを生成。
        複数の生データから新しい知識を合成。
        """
        facilities = [n for n, d in self.graph.nodes(data=True)
                     if d.get('label') == 'Facility']
        
        for facility in facilities:
            facility_data = self.graph.nodes[facility]
            
            # 原単位メトリクスを取得
            intensity_metrics = [n for n in self.graph.successors(facility)
                                if self.graph.nodes[n].get('label') == 'IntensityMetrics']
            
            if intensity_metrics:
                # 集約統計を計算
                co2_values = [self.graph.nodes[n]['co2_intensity_kg_per_kwh'] 
                            for n in intensity_metrics]
                renewable_values = [self.graph.nodes[n]['renewable_ratio']
                                   for n in intensity_metrics]
                
                # 集約ノードを作成
                agg_id = f"AGG_{facility}_2024"
                self.graph.add_node(
                    agg_id,
                    label='AggregationReport',
                    facility_id=facility,
                    facility_name=facility_data['name'],
                    facility_type=facility_data['facility_type'],
                    period='2024-Q1',
                    avg_co2_intensity=round(sum(co2_values)/len(co2_values), 4),
                    max_co2_intensity=round(max(co2_values), 4),
                    min_co2_intensity=round(min(co2_values), 4),
                    avg_renewable_ratio=round(sum(renewable_values)/len(renewable_values), 3),
                    num_records=len(intensity_metrics),
                    aggregation_type='facility_summary'
                )
                
                # 関係を追加
                self.graph.add_edge(facility, agg_id, label='HAS_AGGREGATION')
                
                for metric in intensity_metrics:
                    self.graph.add_edge(agg_id, metric, label='AGGREGATES')
        
        self.transformations.append({
            'type': 'aggregation',
            'description': '施設別集約レポートノードの生成',
            'count': len(facilities)
        })
        print(f"✓ 集約レポートノードを{len(facilities)}件生成しました")
    
    def get_transformation_summary(self) -> List[Dict[str, Any]]:
        """適用された変換の概要を取得"""
        return self.transformations


if __name__ == '__main__':
    from graph_builder import LPGBuilder
    from pathlib import Path
    
    # グラフを構築
    builder = LPGBuilder()
    data_dir = Path(__file__).parent.parent / 'data'
    
    builder.load_facilities(data_dir / 'facilities.csv')
    builder.load_emissions(data_dir / 'emissions.csv')
    builder.load_energy(data_dir / 'energy.csv')
    
    print("\n=== 知識変換を開始 ===")
    transformer = KnowledgeTransformer(builder.graph)
    
    transformer.link_emission_and_energy()
    transformer.calculate_intensity_metrics()
    transformer.classify_performance()
    transformer.create_aggregation_nodes()
    
    print("\n=== 変換完了後のグラフ統計 ===")
    stats = builder.get_graph_stats()
    print(f"ノード総数: {stats['total_nodes']}")
    print(f"エッジ総数: {stats['total_edges']}")
    print(f"ノードタイプ: {stats['node_types']}")
