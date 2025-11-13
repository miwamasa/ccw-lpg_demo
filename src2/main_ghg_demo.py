"""
GHG Report Generation Demo

Manufacturing Ontology から GHG Report Ontology への変換デモ
"""

import argparse
from pathlib import Path
from metadata_loader import MetadataLoader
from dynamic_graph_builder import DynamicGraphBuilder
from rule_engine import RuleEngine
import pandas as pd


def main():
    """メイン処理"""
    print("=" * 70)
    print("GHG排出量レポート生成デモ")
    print("Manufacturing Ontology → GHG Report Ontology")
    print("=" * 70)

    try:
        # 1. Manufacturing Ontology のグラフを構築
        print("\n[ステップ1] Manufacturing Ontology グラフの構築")
        loader = MetadataLoader()
        mfg_schema = loader.load_schema("config/manufacturing_schema.json")

        builder = DynamicGraphBuilder(mfg_schema, base_path=".")
        graph = builder.build_graph()

        # 2. GHG Report Ontology への変換
        print("\n[ステップ2] GHG Report Ontology への変換")
        ghg_trans_def = loader.load_transformations("config/ghg_transformations.json")

        engine = RuleEngine(graph, builder)
        transformations = loader.get_enabled_transformations()
        engine.apply_transformations(transformations)

        # 3. 最終統計の表示
        print("\n[ステップ3] 変換結果の確認")
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

        # 4. GHGレポート生成
        print("\n[ステップ4] GHGレポート生成")
        output_dir = Path("output/ghg")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 排出量詳細レポート
        generate_emissions_detail(graph, output_dir)

        # 活動別集約レポート
        generate_activity_aggregation(graph, output_dir)

        # 組織全体サマリー
        generate_organization_summary(graph, output_dir)

        print(f"\n✓ レポートを {output_dir} に出力しました")

        print("\n" + "=" * 70)
        print("処理が正常に完了しました")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


def generate_emissions_detail(graph, output_dir: Path):
    """
    排出量詳細レポートを生成
    """
    # Emissionノードを取得
    emission_nodes = [n for n, d in graph.nodes(data=True)
                     if d.get('label') == 'Emission']

    if not emission_nodes:
        print("  排出量ノードが見つかりません")
        return

    # データを収集
    emissions_data = []
    for node in emission_nodes:
        node_data = graph.nodes[node]

        # 関連する活動を取得
        activity_name = ""
        facility = ""
        organization = ""
        for predecessor in graph.predecessors(node):
            pred_data = graph.nodes[predecessor]
            if pred_data.get('label') == 'ManufacturingActivity':
                activity_name = pred_data.get('activity_name', '')
                facility = pred_data.get('facility', '')
                organization = pred_data.get('organization_name', '')
                break

        emissions_data.append({
            'emission_id': node,
            'organization': organization,
            'facility': facility,
            'activity_name': activity_name,
            'emission_source': node_data.get('emission_source', ''),
            'source_category': node_data.get('source_category', ''),
            'scope': node_data.get('scope', ''),
            'energy_type': node_data.get('energy_type_name', ''),
            'energy_amount': node_data.get('energy_amount', 0),
            'energy_unit': node_data.get('energy_unit', ''),
            'emission_factor': node_data.get('emission_factor', 0),
            'co2_amount_kg': node_data.get('co2_amount_kg', 0),
            'calculation_method': node_data.get('calculation_method', '')
        })

    # DataFrameに変換して保存
    df = pd.DataFrame(emissions_data)
    df = df.sort_values(['facility', 'activity_name'])
    output_path = output_dir / 'emissions_detail.csv'
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"  ✓ 排出量詳細レポート: {output_path} ({len(df)}件)")


def generate_activity_aggregation(graph, output_dir: Path):
    """
    活動別集約レポートを生成
    """
    # ScopeAggregationノードを取得
    agg_nodes = [n for n, d in graph.nodes(data=True)
                if d.get('label') == 'ScopeAggregation']

    if not agg_nodes:
        print("  集約ノードが見つかりません")
        return

    # データを収集
    agg_data = []
    for node in agg_nodes:
        node_data = graph.nodes[node]

        agg_data.append({
            'activity_id': node_data.get('activity_id', ''),
            'activity_name': node_data.get('activity_name', ''),
            'facility': node_data.get('facility', ''),
            'organization': node_data.get('organization_name', ''),
            'start_date': node_data.get('start_date', ''),
            'end_date': node_data.get('end_date', ''),
            'scope1_emissions_kg': node_data.get('total_scope1_kg', 0),
            'scope2_emissions_kg': node_data.get('total_scope2_kg', 0),
            'total_emissions_kg': node_data.get('total_emissions_kg', 0),
            'num_emission_sources': node_data.get('num_emission_sources', 0)
        })

    # DataFrameに変換して保存
    df = pd.DataFrame(agg_data)
    df = df.sort_values(['facility', 'activity_name'])
    output_path = output_dir / 'activity_aggregation.csv'
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"  ✓ 活動別集約レポート: {output_path} ({len(df)}件)")


def generate_organization_summary(graph, output_dir: Path):
    """
    組織全体のサマリーレポートを生成
    """
    # ScopeAggregationノードから組織全体を集計
    agg_nodes = [n for n, d in graph.nodes(data=True)
                if d.get('label') == 'ScopeAggregation']

    if not agg_nodes:
        print("  集約データがありません")
        return

    # 組織名を取得
    org_name = graph.nodes[agg_nodes[0]].get('organization_name', 'Unknown Organization')

    # 合計を計算
    total_scope1 = sum(graph.nodes[n].get('total_scope1_kg', 0) for n in agg_nodes)
    total_scope2 = sum(graph.nodes[n].get('total_scope2_kg', 0) for n in agg_nodes)
    total_emissions = sum(graph.nodes[n].get('total_emissions_kg', 0) for n in agg_nodes)

    # Emissionノード数
    emission_nodes = [n for n, d in graph.nodes(data=True)
                     if d.get('label') == 'Emission']

    # 報告期間を取得
    activities = [n for n, d in graph.nodes(data=True)
                 if d.get('label') == 'ManufacturingActivity']
    start_dates = [graph.nodes[n].get('start_date') for n in activities]
    end_dates = [graph.nodes[n].get('end_date') for n in activities]
    reporting_period = f"{min(start_dates)} to {max(end_dates)}"

    # サマリーデータ
    summary_data = [{
        'report_id': f"GHG-{org_name.replace(' ', '')}-202401",
        'organization_name': org_name,
        'reporting_period': reporting_period,
        'total_scope1_emissions_kg': round(total_scope1, 2),
        'total_scope2_emissions_kg': round(total_scope2, 2),
        'total_emissions_kg': round(total_emissions, 2),
        'num_activities': len(agg_nodes),
        'num_emission_sources': len(emission_nodes),
        'report_date': pd.Timestamp.now().strftime('%Y-%m-%d')
    }]

    # DataFrameに変換して保存
    df = pd.DataFrame(summary_data)
    output_path = output_dir / 'organization_summary.csv'
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"  ✓ 組織サマリーレポート: {output_path}")

    # サマリー情報を表示
    print(f"\n  === GHG排出量レポートサマリー ===")
    print(f"  組織名: {org_name}")
    print(f"  報告期間: {reporting_period}")
    print(f"  Scope1排出量: {total_scope1:,.2f} kg-CO2")
    print(f"  Scope2排出量: {total_scope2:,.2f} kg-CO2")
    print(f"  総排出量: {total_emissions:,.2f} kg-CO2")
    print(f"  活動数: {len(agg_nodes)}")
    print(f"  排出源数: {len(emission_nodes)}")


if __name__ == '__main__':
    exit(main())
