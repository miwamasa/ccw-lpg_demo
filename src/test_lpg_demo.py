"""
Test Cases for LPG Knowledge Transformation Demo

各モジュールの機能を検証するテストケース
"""

import unittest
import networkx as nx
import pandas as pd
from pathlib import Path
import sys
import tempfile
import shutil

# src ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from graph_builder import LPGBuilder
from knowledge_transform import KnowledgeTransformer
from report_generator import ReportGenerator


class TestLPGBuilder(unittest.TestCase):
    """LPGBuilder クラスのテストケース"""
    
    def setUp(self):
        """各テストの前処理"""
        self.builder = LPGBuilder()
        self.data_dir = Path(__file__).parent.parent / 'data'
    
    def test_graph_initialization(self):
        """グラフが正しく初期化されるかテスト"""
        self.assertIsInstance(self.builder.graph, nx.MultiDiGraph)
        self.assertEqual(self.builder.graph.number_of_nodes(), 0)
        self.assertEqual(self.builder.graph.number_of_edges(), 0)
    
    def test_load_facilities(self):
        """施設データの読み込みテスト"""
        self.builder.load_facilities(self.data_dir / 'facilities.csv')
        
        # ノード数の確認
        self.assertEqual(self.builder.graph.number_of_nodes(), 5)
        
        # ノードのラベルとプロパティの確認
        for node, data in self.builder.graph.nodes(data=True):
            self.assertEqual(data['label'], 'Facility')
            self.assertIn('name', data)
            self.assertIn('facility_type', data)
            self.assertIn('location', data)
            self.assertIn('capacity', data)
        
        # 特定のノードの確認
        self.assertTrue(self.builder.graph.has_node('F001'))
        f001_data = self.builder.graph.nodes['F001']
        self.assertEqual(f001_data['name'], '東京工場')
        self.assertEqual(f001_data['facility_type'], '製造')
    
    def test_load_emissions(self):
        """排出量データの読み込みテスト"""
        self.builder.load_facilities(self.data_dir / 'facilities.csv')
        self.builder.load_emissions(self.data_dir / 'emissions.csv')
        
        # 排出記録ノードの確認
        emission_nodes = [n for n, d in self.builder.graph.nodes(data=True)
                         if d.get('label') == 'EmissionRecord']
        self.assertEqual(len(emission_nodes), 10)
        
        # エッジの確認
        edges = list(self.builder.graph.edges(data=True))
        has_emission_edges = [e for e in edges if e[2].get('label') == 'HAS_EMISSION']
        self.assertEqual(len(has_emission_edges), 10)
    
    def test_load_energy(self):
        """エネルギーデータの読み込みテスト"""
        self.builder.load_facilities(self.data_dir / 'facilities.csv')
        self.builder.load_energy(self.data_dir / 'energy.csv')
        
        # エネルギー記録ノードの確認
        energy_nodes = [n for n, d in self.builder.graph.nodes(data=True)
                       if d.get('label') == 'EnergyRecord']
        self.assertEqual(len(energy_nodes), 10)
        
        # エッジの確認
        edges = list(self.builder.graph.edges(data=True))
        has_energy_edges = [e for e in edges if e[2].get('label') == 'HAS_ENERGY']
        self.assertEqual(len(has_energy_edges), 10)
    
    def test_get_graph_stats(self):
        """グラフ統計情報の取得テスト"""
        self.builder.load_facilities(self.data_dir / 'facilities.csv')
        self.builder.load_emissions(self.data_dir / 'emissions.csv')
        
        stats = self.builder.get_graph_stats()
        
        self.assertEqual(stats['total_nodes'], 15)  # 5施設 + 10排出記録
        self.assertEqual(stats['total_edges'], 10)
        self.assertEqual(stats['node_types']['Facility'], 5)
        self.assertEqual(stats['node_types']['EmissionRecord'], 10)


class TestKnowledgeTransformer(unittest.TestCase):
    """KnowledgeTransformer クラスのテストケース"""
    
    def setUp(self):
        """各テストの前処理：完全なグラフを構築"""
        self.builder = LPGBuilder()
        data_dir = Path(__file__).parent.parent / 'data'
        
        self.builder.load_facilities(data_dir / 'facilities.csv')
        self.builder.load_emissions(data_dir / 'emissions.csv')
        self.builder.load_energy(data_dir / 'energy.csv')
        
        self.transformer = KnowledgeTransformer(self.builder.graph)
        self.initial_node_count = self.builder.graph.number_of_nodes()
        self.initial_edge_count = self.builder.graph.number_of_edges()
    
    def test_link_emission_and_energy(self):
        """排出とエネルギーのリンク生成テスト"""
        self.transformer.link_emission_and_energy()
        
        # 新しいエッジが追加されたか確認
        self.assertGreater(self.builder.graph.number_of_edges(), 
                          self.initial_edge_count)
        
        # CORRELATES_WITH エッジの確認
        edges = list(self.builder.graph.edges(data=True, keys=True))
        correlates_edges = [e for e in edges 
                           if e[3].get('label') == 'CORRELATES_WITH']
        self.assertGreater(len(correlates_edges), 0)
        
        # エッジのプロパティ確認
        edge_data = correlates_edges[0][3]
        self.assertEqual(edge_data['relation_type'], 'temporal_match')
        self.assertEqual(edge_data['created_by'], 'transformer')
    
    def test_calculate_intensity_metrics(self):
        """原単位メトリクス計算テスト"""
        self.transformer.link_emission_and_energy()
        self.transformer.calculate_intensity_metrics()
        
        # IntensityMetrics ノードの確認
        intensity_nodes = [n for n, d in self.builder.graph.nodes(data=True)
                          if d.get('label') == 'IntensityMetrics']
        self.assertGreater(len(intensity_nodes), 0)
        
        # ノードのプロパティ確認
        intensity_data = self.builder.graph.nodes[intensity_nodes[0]]
        self.assertIn('co2_intensity_kg_per_kwh', intensity_data)
        self.assertIn('water_intensity_m3_per_kwh', intensity_data)
        self.assertIn('renewable_ratio', intensity_data)
        self.assertEqual(intensity_data['derived_from'], 'emission_and_energy')
    
    def test_classify_performance(self):
        """パフォーマンス分類テスト"""
        self.transformer.link_emission_and_energy()
        self.transformer.calculate_intensity_metrics()
        self.transformer.classify_performance()
        
        # パフォーマンス評価が付与されているか確認
        intensity_nodes = [n for n, d in self.builder.graph.nodes(data=True)
                          if d.get('label') == 'IntensityMetrics']
        
        for node in intensity_nodes:
            node_data = self.builder.graph.nodes[node]
            self.assertIn('performance_rating', node_data)
            self.assertIn(node_data['performance_rating'],
                         ['Excellent', 'Good', 'Average', 'NeedsImprovement'])
            self.assertIn('avg_benchmark', node_data)
            self.assertIn('rating_timestamp', node_data)
    
    def test_create_aggregation_nodes(self):
        """集約ノード生成テスト"""
        self.transformer.link_emission_and_energy()
        self.transformer.calculate_intensity_metrics()
        self.transformer.create_aggregation_nodes()
        
        # AggregationReport ノードの確認
        agg_nodes = [n for n, d in self.builder.graph.nodes(data=True)
                    if d.get('label') == 'AggregationReport']
        self.assertEqual(len(agg_nodes), 5)  # 5施設分
        
        # ノードのプロパティ確認
        agg_data = self.builder.graph.nodes[agg_nodes[0]]
        self.assertIn('facility_id', agg_data)
        self.assertIn('avg_co2_intensity', agg_data)
        self.assertIn('max_co2_intensity', agg_data)
        self.assertIn('min_co2_intensity', agg_data)
        self.assertIn('avg_renewable_ratio', agg_data)
        self.assertIn('num_records', agg_data)
    
    def test_transformation_summary(self):
        """変換サマリーの取得テスト"""
        self.transformer.link_emission_and_energy()
        self.transformer.calculate_intensity_metrics()
        
        summary = self.transformer.get_transformation_summary()
        
        self.assertEqual(len(summary), 2)
        self.assertEqual(summary[0]['type'], 'cross_linking')
        self.assertEqual(summary[1]['type'], 'metric_derivation')


class TestReportGenerator(unittest.TestCase):
    """ReportGenerator クラスのテストケース"""
    
    def setUp(self):
        """各テストの前処理：変換済みグラフを準備"""
        builder = LPGBuilder()
        data_dir = Path(__file__).parent.parent / 'data'
        
        builder.load_facilities(data_dir / 'facilities.csv')
        builder.load_emissions(data_dir / 'emissions.csv')
        builder.load_energy(data_dir / 'energy.csv')
        
        transformer = KnowledgeTransformer(builder.graph)
        transformer.link_emission_and_energy()
        transformer.calculate_intensity_metrics()
        transformer.classify_performance()
        transformer.create_aggregation_nodes()
        
        self.generator = ReportGenerator(builder.graph)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """テスト後の後処理"""
        shutil.rmtree(self.temp_dir)
    
    def test_generate_environmental_report(self):
        """環境レポート生成テスト"""
        report = self.generator.generate_environmental_report()
        
        # DataFrameの基本確認
        self.assertIsInstance(report, pd.DataFrame)
        self.assertEqual(len(report), 5)  # 5施設分
        
        # カラムの確認
        expected_columns = [
            '施設ID', '施設名', '施設タイプ', '所在地', '評価期間',
            'CO2排出量_合計_kg', '電力使用量_合計_kWh', '水使用量_合計_m3',
            '廃棄物量_合計_kg', 'CO2排出原単位_平均_kg/kWh',
            'パフォーマンス評価', 'データ件数'
        ]
        for col in expected_columns:
            self.assertIn(col, report.columns)
        
        # データの妥当性確認
        self.assertTrue((report['CO2排出量_合計_kg'] > 0).all())
        self.assertTrue((report['電力使用量_合計_kWh'] > 0).all())
        self.assertTrue((report['データ件数'] > 0).all())
    
    def test_generate_detailed_metrics_report(self):
        """詳細メトリクスレポート生成テスト"""
        report = self.generator.generate_detailed_metrics_report()
        
        # DataFrameの基本確認
        self.assertIsInstance(report, pd.DataFrame)
        self.assertGreater(len(report), 0)
        
        # カラムの確認
        expected_columns = [
            '施設ID', '施設名', '年', '月',
            'CO2排出量_kg', '電力使用量_kWh', 'ガス使用量_m3',
            'CO2原単位_kg/kWh', '再生可能エネルギー比率', 'パフォーマンス評価'
        ]
        for col in expected_columns:
            self.assertIn(col, report.columns)
        
        # データ型の確認
        self.assertEqual(report['年'].dtype, 'int64')
        self.assertEqual(report['月'].dtype, 'int64')
    
    def test_save_report(self):
        """レポート保存テスト"""
        report = self.generator.generate_environmental_report()
        output_path = Path(self.temp_dir)
        filename = 'test_report.csv'
        
        self.generator.save_report(report, filename, output_path)
        
        # ファイルが存在するか確認
        saved_file = output_path / filename
        self.assertTrue(saved_file.exists())
        
        # 保存されたファイルが読み込めるか確認
        loaded_df = pd.read_csv(saved_file)
        self.assertEqual(len(loaded_df), len(report))


class TestIntegration(unittest.TestCase):
    """統合テスト：全体フローの確認"""
    
    def test_full_pipeline(self):
        """完全なパイプラインテスト"""
        # グラフ構築
        builder = LPGBuilder()
        data_dir = Path(__file__).parent.parent / 'data'
        
        builder.load_facilities(data_dir / 'facilities.csv')
        builder.load_emissions(data_dir / 'emissions.csv')
        builder.load_energy(data_dir / 'energy.csv')
        
        initial_stats = builder.get_graph_stats()
        
        # 知識変換
        transformer = KnowledgeTransformer(builder.graph)
        transformer.link_emission_and_energy()
        transformer.calculate_intensity_metrics()
        transformer.classify_performance()
        transformer.create_aggregation_nodes()
        
        final_stats = builder.get_graph_stats()
        
        # グラフが拡張されたことを確認
        self.assertGreater(final_stats['total_nodes'], initial_stats['total_nodes'])
        self.assertGreater(final_stats['total_edges'], initial_stats['total_edges'])
        
        # レポート生成
        generator = ReportGenerator(builder.graph)
        env_report = generator.generate_environmental_report()
        detail_report = generator.generate_detailed_metrics_report()
        
        # レポートが生成されたことを確認
        self.assertIsInstance(env_report, pd.DataFrame)
        self.assertIsInstance(detail_report, pd.DataFrame)
        self.assertGreater(len(env_report), 0)
        self.assertGreater(len(detail_report), 0)


def run_tests():
    """テストスイートを実行"""
    # テストスイートを作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 各テストクラスを追加
    suite.addTests(loader.loadTestsFromTestCase(TestLPGBuilder))
    suite.addTests(loader.loadTestsFromTestCase(TestKnowledgeTransformer))
    suite.addTests(loader.loadTestsFromTestCase(TestReportGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # テストを実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト実行結果サマリー")
    print("=" * 60)
    print(f"実行テスト数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失敗: {len(result.failures)}")
    print(f"エラー: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
