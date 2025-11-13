"""
Generic LPG System - Main Entry Point

メタデータ駆動型のLabeled Property Graphシステムのメイン実行スクリプト
"""

import argparse
from pathlib import Path
from metadata_loader import MetadataLoader
from dynamic_graph_builder import DynamicGraphBuilder
from rule_engine import RuleEngine


def main():
    """メイン処理"""
    # コマンドライン引数のパース
    parser = argparse.ArgumentParser(
        description="汎用的LPGシステム - メタデータ駆動型のグラフ構築・変換システム"
    )
    parser.add_argument(
        "--schema",
        type=str,
        default="config/schema.json",
        help="スキーマファイルのパス (デフォルト: config/schema.json)"
    )
    parser.add_argument(
        "--transformations",
        type=str,
        default="config/transformations.json",
        help="変換ルールファイルのパス (デフォルト: config/transformations.json)"
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default=".",
        help="データファイルの基準パス (デフォルト: .)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output",
        help="出力ディレクトリ (デフォルト: output)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("汎用的LPGシステム")
    print("メタデータ駆動型のグラフ構築・変換システム")
    print("=" * 60)

    try:
        # 1. メタデータの読み込み
        print("\n[ステップ1] メタデータの読み込み")
        loader = MetadataLoader()
        schema = loader.load_schema(args.schema)
        transformations_def = loader.load_transformations(args.transformations)

        # 2. グラフの構築
        print("\n[ステップ2] グラフの構築")
        builder = DynamicGraphBuilder(schema, base_path=args.base_path)
        graph = builder.build_graph()

        # 3. 知識変換の適用
        print("\n[ステップ3] 知識変換の適用")
        engine = RuleEngine(graph, builder)
        transformations = loader.get_enabled_transformations()
        engine.apply_transformations(transformations)

        # 4. 最終統計の表示
        print("\n[ステップ4] 最終結果")
        stats = builder.get_graph_stats()
        print(f"\n最終グラフ統計:")
        print(f"  ノード総数: {stats['total_nodes']}")
        print(f"  エッジ総数: {stats['total_edges']}")
        print(f"\nノードタイプ:")
        for node_type, count in stats['node_types'].items():
            print(f"  - {node_type}: {count}件")
        print(f"\nエッジタイプ:")
        for edge_type, count in stats['edge_types'].items():
            print(f"  - {edge_type}: {count}件")

        # 5. レポート生成（オプション）
        print("\n[ステップ5] レポート生成")
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 環境レポートの生成
        generate_environmental_report(graph, builder, output_dir)

        # 詳細メトリクスの生成
        generate_detailed_metrics(graph, builder, output_dir)

        print(f"\n✓ レポートを {output_dir} に出力しました")

        print("\n" + "=" * 60)
        print("処理が正常に完了しました")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


def generate_environmental_report(graph, builder, output_dir: Path):
    """
    環境パフォーマンスレポートを生成

    Args:
        graph: グラフ
        builder: グラフビルダー
        output_dir: 出力ディレクトリ
    """
    import pandas as pd

    # 集約レポートノードを取得
    agg_nodes = [n for n, d in graph.nodes(data=True)
                if d.get('label') == 'AggregationReport']

    if not agg_nodes:
        print("  集約レポートノードが見つかりません")
        return

    # データを収集
    report_data = []
    for node in agg_nodes:
        node_data = graph.nodes[node]

        # パフォーマンス評価を取得（関連するIntensityMetricsから）
        performance_ratings = []
        for predecessor in graph.predecessors(node):
            pred_data = graph.nodes[predecessor]
            if pred_data.get('label') == 'IntensityMetrics':
                if 'performance_rating' in pred_data:
                    performance_ratings.append(pred_data['performance_rating'])

        # 最も多い評価を使用
        if performance_ratings:
            from collections import Counter
            performance = Counter(performance_ratings).most_common(1)[0][0]
        else:
            performance = 'Unknown'

        report_data.append({
            'facility_id': node_data.get('facility_id', ''),
            'facility_name': node_data.get('facility_name', ''),
            'facility_type': node_data.get('facility_type', ''),
            'avg_co2_intensity': node_data.get('avg_co2_intensity', 0),
            'max_co2_intensity': node_data.get('max_co2_intensity', 0),
            'min_co2_intensity': node_data.get('min_co2_intensity', 0),
            'avg_renewable_ratio': node_data.get('avg_renewable_ratio', 0),
            'num_records': node_data.get('num_records', 0),
            'performance_rating': performance,
            'period': node_data.get('period', '')
        })

    # DataFrameに変換して保存
    df = pd.DataFrame(report_data)
    output_path = output_dir / 'environmental_report.csv'
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"  ✓ 環境レポート: {output_path} ({len(df)}件)")


def generate_detailed_metrics(graph, builder, output_dir: Path):
    """
    詳細メトリクスレポートを生成

    Args:
        graph: グラフ
        builder: グラフビルダー
        output_dir: 出力ディレクトリ
    """
    import pandas as pd

    # IntensityMetricsノードを取得
    intensity_nodes = [n for n, d in graph.nodes(data=True)
                      if d.get('label') == 'IntensityMetrics']

    if not intensity_nodes:
        print("  原単位メトリクスノードが見つかりません")
        return

    # データを収集
    metrics_data = []
    for node in intensity_nodes:
        node_data = graph.nodes[node]

        # 施設情報を取得
        facility_id = None
        facility_name = None
        for predecessor in graph.predecessors(node):
            pred_data = graph.nodes[predecessor]
            if pred_data.get('label') == 'Facility':
                facility_id = predecessor
                facility_name = pred_data.get('name', '')
                break

        metrics_data.append({
            'facility_id': facility_id or '',
            'facility_name': facility_name or '',
            'year': node_data.get('year', ''),
            'month': node_data.get('month', ''),
            'co2_intensity_kg_per_kwh': node_data.get('co2_intensity_kg_per_kwh', 0),
            'water_intensity_m3_per_kwh': node_data.get('water_intensity_m3_per_kwh', 0),
            'renewable_ratio': node_data.get('renewable_ratio', 0),
            'performance_rating': node_data.get('performance_rating', ''),
            'avg_benchmark': node_data.get('avg_benchmark', 0)
        })

    # DataFrameに変換して保存
    df = pd.DataFrame(metrics_data)
    df = df.sort_values(['facility_id', 'year', 'month'])
    output_path = output_dir / 'detailed_metrics.csv'
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"  ✓ 詳細メトリクス: {output_path} ({len(df)}件)")


if __name__ == '__main__':
    exit(main())
