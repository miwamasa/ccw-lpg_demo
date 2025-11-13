"""
Report Generator Module

変換・合成されたLPGから環境データシートを生成します。
グラフの知識を構造化データとして外部出力。
"""

import networkx as nx
import pandas as pd
from typing import List, Dict, Any
from pathlib import Path


class ReportGenerator:
    """
    LPGから環境データシートを生成するクラス
    
    グラフの柔軟な構造から、特定のフォーマットのレポートを抽出。
    """
    
    def __init__(self, graph: nx.MultiDiGraph):
        """
        Args:
            graph: レポート生成元のLPG
        """
        self.graph = graph
    
    def generate_environmental_report(self) -> pd.DataFrame:
        """
        環境パフォーマンスレポートを生成
        
        集約ノードと原単位メトリクスを組み合わせて、
        包括的な環境データシートを作成。
        
        Returns:
            環境データシートのDataFrame
        """
        report_data = []
        
        # 集約レポートノードを取得
        agg_nodes = [n for n, d in self.graph.nodes(data=True)
                    if d.get('label') == 'AggregationReport']
        
        for agg_node in agg_nodes:
            agg_data = self.graph.nodes[agg_node]
            
            # この集約ノードに関連する原単位メトリクスを取得
            metrics = [n for n in self.graph.successors(agg_node)
                      if self.graph.nodes[n].get('label') == 'IntensityMetrics']
            
            # 施設情報を取得
            facility_id = agg_data['facility_id']
            facility_data = self.graph.nodes[facility_id]
            
            # パフォーマンス評価を集計
            performance_counts = {}
            for metric in metrics:
                perf = self.graph.nodes[metric].get('performance_rating', 'Unknown')
                performance_counts[perf] = performance_counts.get(perf, 0) + 1
            
            # 最も多いパフォーマンス評価を採用
            dominant_performance = max(performance_counts.items(), 
                                      key=lambda x: x[1])[0] if performance_counts else 'N/A'
            
            # 排出量と廃棄物の合計を計算
            total_co2 = 0
            total_waste = 0
            total_water = 0
            total_electricity = 0
            
            for metric in metrics:
                # メトリクスから排出記録を辿る
                emi_records = [n for n in self.graph.successors(metric)
                              if self.graph.nodes[n].get('label') == 'EmissionRecord']
                ene_records = [n for n in self.graph.successors(metric)
                              if self.graph.nodes[n].get('label') == 'EnergyRecord']
                
                for emi in emi_records:
                    emi_data = self.graph.nodes[emi]
                    total_co2 += emi_data.get('co2_emissions_kg', 0)
                    total_waste += emi_data.get('waste_kg', 0)
                    total_water += emi_data.get('water_usage_m3', 0)
                
                for ene in ene_records:
                    ene_data = self.graph.nodes[ene]
                    total_electricity += ene_data.get('electricity_kwh', 0)
            
            # レポート行を作成
            report_row = {
                '施設ID': facility_id,
                '施設名': agg_data['facility_name'],
                '施設タイプ': agg_data['facility_type'],
                '所在地': facility_data['location'],
                '評価期間': agg_data['period'],
                'CO2排出量_合計_kg': total_co2,
                '電力使用量_合計_kWh': total_electricity,
                '水使用量_合計_m3': total_water,
                '廃棄物量_合計_kg': total_waste,
                'CO2排出原単位_平均_kg/kWh': agg_data['avg_co2_intensity'],
                'CO2排出原単位_最大_kg/kWh': agg_data['max_co2_intensity'],
                'CO2排出原単位_最小_kg/kWh': agg_data['min_co2_intensity'],
                '再生可能エネルギー比率_平均': agg_data['avg_renewable_ratio'],
                'パフォーマンス評価': dominant_performance,
                'データ件数': agg_data['num_records']
            }
            
            report_data.append(report_row)
        
        df = pd.DataFrame(report_data)
        
        # 追加の計算列
        if len(df) > 0:
            df['CO2削減ポテンシャル_kg'] = (
                df['CO2排出量_合計_kg'] - 
                df['CO2排出量_合計_kg'].min()
            )
            df['ベンチマーク比'] = (
                df['CO2排出原単位_平均_kg/kWh'] / 
                df['CO2排出原単位_平均_kg/kWh'].mean()
            )
        
        return df
    
    def generate_detailed_metrics_report(self) -> pd.DataFrame:
        """
        月次の詳細メトリクスレポートを生成
        
        Returns:
            詳細メトリクスのDataFrame
        """
        report_data = []
        
        # 原単位メトリクスノードを取得
        intensity_nodes = [n for n, d in self.graph.nodes(data=True)
                          if d.get('label') == 'IntensityMetrics']
        
        for node in intensity_nodes:
            node_data = self.graph.nodes[node]
            
            # 施設情報を取得
            facility = [n for n in self.graph.predecessors(node)
                       if self.graph.nodes[n].get('label') == 'Facility'][0]
            facility_data = self.graph.nodes[facility]
            
            # 排出・エネルギー情報を取得
            emi_records = [n for n in self.graph.successors(node)
                          if self.graph.nodes[n].get('label') == 'EmissionRecord']
            ene_records = [n for n in self.graph.successors(node)
                          if self.graph.nodes[n].get('label') == 'EnergyRecord']
            
            if emi_records and ene_records:
                emi_data = self.graph.nodes[emi_records[0]]
                ene_data = self.graph.nodes[ene_records[0]]
                
                report_row = {
                    '施設ID': facility,
                    '施設名': facility_data['name'],
                    '年': node_data['year'],
                    '月': node_data['month'],
                    'CO2排出量_kg': emi_data['co2_emissions_kg'],
                    '電力使用量_kWh': ene_data['electricity_kwh'],
                    'ガス使用量_m3': ene_data['gas_m3'],
                    '水使用量_m3': emi_data['water_usage_m3'],
                    '廃棄物量_kg': emi_data['waste_kg'],
                    'CO2原単位_kg/kWh': node_data['co2_intensity_kg_per_kwh'],
                    '水使用原単位_m3/kWh': node_data['water_intensity_m3_per_kwh'],
                    '再生可能エネルギー比率': ene_data['renewable_ratio'],
                    'パフォーマンス評価': node_data.get('performance_rating', 'N/A')
                }
                
                report_data.append(report_row)
        
        return pd.DataFrame(report_data)
    
    def save_report(self, df: pd.DataFrame, filename: str, output_dir: Path) -> None:
        """
        レポートをCSVファイルとして保存
        
        Args:
            df: 保存するDataFrame
            filename: ファイル名
            output_dir: 出力ディレクトリ
        """
        output_dir.mkdir(exist_ok=True, parents=True)
        output_path = output_dir / filename
        
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"✓ レポートを保存しました: {output_path}")
    
    def print_summary(self, df: pd.DataFrame) -> None:
        """
        レポートのサマリーを表示
        
        Args:
            df: サマリー対象のDataFrame
        """
        print("\n=== 環境データシート サマリー ===")
        print(f"対象施設数: {len(df)}")
        
        if 'CO2排出量_合計_kg' in df.columns:
            print(f"総CO2排出量: {df['CO2排出量_合計_kg'].sum():,.0f} kg")
            print(f"平均CO2排出原単位: {df['CO2排出原単位_平均_kg/kWh'].mean():.4f} kg/kWh")
        
        if 'パフォーマンス評価' in df.columns:
            print("\nパフォーマンス評価分布:")
            for rating, count in df['パフォーマンス評価'].value_counts().items():
                print(f"  {rating}: {count}件")


if __name__ == '__main__':
    from graph_builder import LPGBuilder
    from knowledge_transform import KnowledgeTransformer
    from pathlib import Path
    
    # グラフを構築
    builder = LPGBuilder()
    data_dir = Path(__file__).parent.parent / 'data'
    
    builder.load_facilities(data_dir / 'facilities.csv')
    builder.load_emissions(data_dir / 'emissions.csv')
    builder.load_energy(data_dir / 'energy.csv')
    
    # 知識変換
    transformer = KnowledgeTransformer(builder.graph)
    transformer.link_emission_and_energy()
    transformer.calculate_intensity_metrics()
    transformer.classify_performance()
    transformer.create_aggregation_nodes()
    
    # レポート生成
    print("\n=== レポート生成 ===")
    generator = ReportGenerator(builder.graph)
    
    env_report = generator.generate_environmental_report()
    generator.print_summary(env_report)
    
    output_dir = Path(__file__).parent.parent / 'output'
    generator.save_report(env_report, 'environmental_report.csv', output_dir)
    
    detail_report = generator.generate_detailed_metrics_report()
    generator.save_report(detail_report, 'detailed_metrics.csv', output_dir)
