"""
LPG Knowledge Transformation Demo - Main Script

CSVデータをLPGに変換し、知識の変換・合成を行い、
環境データシートとして出力する一連のフローを実行します。
"""

from pathlib import Path
from graph_builder import LPGBuilder
from knowledge_transform import KnowledgeTransformer
from report_generator import ReportGenerator


def main():
    """メイン実行フロー"""
    
    print("=" * 60)
    print("LPG Knowledge Transformation Demo")
    print("=" * 60)
    
    # パス設定
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / 'data'
    output_dir = base_dir / 'output'
    
    # ステップ1: グラフ構築
    print("\n[ステップ1] CSVデータからLPGを構築")
    print("-" * 60)
    builder = LPGBuilder()
    builder.load_facilities(data_dir / 'facilities.csv')
    builder.load_emissions(data_dir / 'emissions.csv')
    builder.load_energy(data_dir / 'energy.csv')
    
    initial_stats = builder.get_graph_stats()
    print(f"\n初期グラフ統計:")
    print(f"  ノード数: {initial_stats['total_nodes']}")
    print(f"  エッジ数: {initial_stats['total_edges']}")
    print(f"  ノードタイプ: {initial_stats['node_types']}")
    
    # ステップ2: 知識変換
    print("\n[ステップ2] 知識の変換と合成")
    print("-" * 60)
    print("LPGの柔軟性を活用して、新しい関係性とノードを追加します...")
    
    transformer = KnowledgeTransformer(builder.graph)
    
    print("\n[変換2-1] データ相関リンク生成")
    transformer.link_emission_and_energy()
    
    print("\n[変換2-2] 派生メトリクス計算")
    transformer.calculate_intensity_metrics()
    
    print("\n[変換2-3] パフォーマンス分類")
    transformer.classify_performance()
    
    print("\n[変換2-4] 集約ノード生成")
    transformer.create_aggregation_nodes()
    
    final_stats = builder.get_graph_stats()
    print(f"\n変換後のグラフ統計:")
    print(f"  ノード数: {final_stats['total_nodes']} "
          f"(+{final_stats['total_nodes'] - initial_stats['total_nodes']})")
    print(f"  エッジ数: {final_stats['total_edges']} "
          f"(+{final_stats['total_edges'] - initial_stats['total_edges']})")
    print(f"  ノードタイプ: {final_stats['node_types']}")
    print(f"  エッジタイプ: {final_stats['edge_types']}")
    
    # 変換サマリー
    print("\n適用された変換:")
    for trans in transformer.get_transformation_summary():
        print(f"  - {trans['description']}: {trans['count']}件")
    
    # ステップ3: レポート生成
    print("\n[ステップ3] 環境データシート生成")
    print("-" * 60)
    
    generator = ReportGenerator(builder.graph)
    
    # 環境パフォーマンスレポート
    env_report = generator.generate_environmental_report()
    generator.print_summary(env_report)
    generator.save_report(env_report, 'environmental_report.csv', output_dir)
    
    # 詳細メトリクスレポート
    detail_report = generator.generate_detailed_metrics_report()
    generator.save_report(detail_report, 'detailed_metrics.csv', output_dir)
    
    print("\n" + "=" * 60)
    print("✓ 全処理が完了しました")
    print("=" * 60)
    print(f"\n出力ファイル:")
    print(f"  - {output_dir / 'environmental_report.csv'}")
    print(f"  - {output_dir / 'detailed_metrics.csv'}")
    
    # LPGの柔軟性のまとめ
    print("\n" + "=" * 60)
    print("LPGの柔軟性のまとめ")
    print("=" * 60)
    print("""
1. スキーマフリーな拡張
   → 既存ノードに動的にプロパティを追加
   → performance_rating, avg_benchmarkなど

2. 多層的な関係性
   → HAS_EMISSION, HAS_ENERGY (基本関係)
   → CORRELATES_WITH (横断的リンク)
   → DERIVED_FROM, AGGREGATES (派生関係)

3. 知識の合成
   → 複数データソース(排出+エネルギー)から新メトリクスを生成
   → 原単位、集約統計などの派生知識

4. メタデータの付与
   → パフォーマンス評価、ベンチマーク比較
   → レポート生成に必要な情報を動的に追加

これらにより、元のCSVデータを変更せずに、
グラフ上で自由に知識を変換・合成できます。
    """)


if __name__ == '__main__':
    main()
