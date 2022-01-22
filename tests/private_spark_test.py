import pyspark
from pyspark import SparkContext
from unittest.mock import patch
import unittest
import sys

import pipeline_dp
from pipeline_dp import aggregate_params as agg
from pipeline_dp import budget_accounting, private_spark


@unittest.skipIf(
    sys.platform == "win32" or
    (sys.version_info.minor <= 7 and sys.version_info.major == 3),
    "There are some problems with PySpark setup on older python and Windows")
class PrivateRDDTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        conf = pyspark.SparkConf()
        cls.sc = SparkContext.getOrCreate(conf=conf)

    def test_map(self):
        data = [(1, 11), (2, 12)]
        dist_data = PrivateRDDTest.sc.parallelize(data)
        budget_accountant = budget_accounting.NaiveBudgetAccountant(1, 1e-10)

        def privacy_id_extractor(x):
            return x[0]

        prdd = private_spark.PrivateRDD(dist_data, budget_accountant,
                                        privacy_id_extractor)

        result = prdd.map(lambda x: (x[0], x[1] * 2))

        self.assertEqual(result._rdd.collect(), [(1, (1, 22)), (2, (2, 24))])
        self.assertEqual(result._budget_accountant, prdd._budget_accountant)

    def test_flatmap(self):
        data = [(1, 11), (2, 12)]
        dist_data = PrivateRDDTest.sc.parallelize(data)
        budget_accountant = budget_accounting.NaiveBudgetAccountant(1, 1e-10)

        def privacy_id_extractor(x):
            return x[0]

        prdd = private_spark.PrivateRDD(dist_data, budget_accountant,
                                        privacy_id_extractor)

        result = prdd.flat_map(lambda x: [(x[0], x[1] * 2),
                                          (x[0], x[1] * 2 + 1)])

        self.assertEqual(result._rdd.collect(), [(1, (1, 22)), (1, (1, 23)),
                                                 (2, (2, 24)), (2, (2, 25))])
        self.assertEqual(result._budget_accountant, prdd._budget_accountant)

    @patch('pipeline_dp.dp_engine.DPEngine.aggregate')
    def test_sum(self, mock_aggregate):
        dist_data = PrivateRDDTest.sc.parallelize([])
        budget_accountant = budget_accounting.NaiveBudgetAccountant(1, 1e-10)

        def privacy_id_extractor(x):
            return f"pid{x%10}"

        prdd = private_spark.make_private(dist_data, budget_accountant,
                                          privacy_id_extractor)

        sum_params = agg.SumParams(
            noise_kind=pipeline_dp.NoiseKind.GAUSSIAN,
            max_partitions_contributed=2,
            max_contributions_per_partition=3,
            min_value=1,
            max_value=5,
            budget_weight=1,
            public_partitions=None,
            partition_extractor=lambda x: f"pk:{x // 10}",
            value_extractor=lambda x: x)
        prdd.sum(sum_params)

        mock_aggregate.assert_called_once()

        args = mock_aggregate.call_args[0]

        rdd = dist_data.map(lambda x: (privacy_id_extractor(x), x))
        self.assertListEqual(args[0].collect(), rdd.collect())

        params = pipeline_dp.AggregateParams(
            noise_kind=pipeline_dp.NoiseKind.GAUSSIAN,
            metrics=[pipeline_dp.Metrics.SUM],
            max_partitions_contributed=sum_params.max_partitions_contributed,
            max_contributions_per_partition=sum_params.
            max_contributions_per_partition,
            min_value=sum_params.min_value,
            max_value=sum_params.max_value,
            public_partitions=sum_params.public_partitions)
        self.assertEqual(args[1], params)

        mock_aggregate.return_value = PrivateRDDTest.sc.parallelize([
            (0, ["sum0"]), (1, ["sum1"])
        ])
        result = prdd.sum(sum_params)
        self.assertEqual([(0, "sum0"), (1, "sum1")], result.collect())

    @patch('pipeline_dp.dp_engine.DPEngine.aggregate')
    def test_count(self, mock_aggregate):
        dist_data = PrivateRDDTest.sc.parallelize([])
        budget_accountant = budget_accounting.NaiveBudgetAccountant(1, 1e-10)

        def privacy_id_extractor(x):
            return f"pid{x%10}"

        prdd = private_spark.make_private(dist_data, budget_accountant,
                                          privacy_id_extractor)

        count_params = agg.CountParams(
            noise_kind=pipeline_dp.NoiseKind.GAUSSIAN,
            max_partitions_contributed=2,
            max_contributions_per_partition=3,
            budget_weight=1,
            public_partitions=None,
            partition_extractor=lambda x: f"pk:{x // 10}")
        prdd.count(count_params)

        mock_aggregate.assert_called_once()

        args = mock_aggregate.call_args[0]

        rdd = dist_data.map(lambda x: (privacy_id_extractor(x), x))
        self.assertListEqual(args[0].collect(), rdd.collect())

        params = pipeline_dp.AggregateParams(
            noise_kind=pipeline_dp.NoiseKind.GAUSSIAN,
            metrics=[pipeline_dp.Metrics.COUNT],
            max_partitions_contributed=count_params.max_partitions_contributed,
            max_contributions_per_partition=count_params.
            max_contributions_per_partition,
            public_partitions=count_params.public_partitions)
        self.assertEqual(args[1], params)

        mock_aggregate.return_value = PrivateRDDTest.sc.parallelize([
            (0, ["count0"]), (1, ["count1"])
        ])
        result = prdd.count(count_params)
        self.assertEqual([(0, "count0"), (1, "count1")], result.collect())

    @patch('pipeline_dp.dp_engine.DPEngine.aggregate')
    def test_privacy_id_count(self, mock_aggregate):
        dist_data = PrivateRDDTest.sc.parallelize([])
        budget_accountant = budget_accounting.NaiveBudgetAccountant(1, 1e-10)

        def privacy_id_extractor(x):
            return f"pid{x%10}"

        prdd = private_spark.make_private(dist_data, budget_accountant,
                                          privacy_id_extractor)

        privacy_id_count_params = agg.PrivacyIdCountParams(
            noise_kind=pipeline_dp.NoiseKind.GAUSSIAN,
            max_partitions_contributed=2,
            budget_weight=1,
            partition_extractor=lambda x: f"pk:{x // 10}")
        prdd.privacy_id_count(privacy_id_count_params)

        mock_aggregate.assert_called_once()

        args = mock_aggregate.call_args[0]

        rdd = dist_data.map(lambda x: (privacy_id_extractor(x), x))
        self.assertListEqual(args[0].collect(), rdd.collect())

        params = pipeline_dp.AggregateParams(
            noise_kind=pipeline_dp.NoiseKind.GAUSSIAN,
            metrics=[pipeline_dp.Metrics.PRIVACY_ID_COUNT],
            max_partitions_contributed=privacy_id_count_params.
            max_partitions_contributed,
            max_contributions_per_partition=1,
            public_partitions=privacy_id_count_params.public_partitions)
        self.assertEqual(args[1], params)

        mock_aggregate.return_value = PrivateRDDTest.sc.parallelize([
            (0, ["count0"]), (1, ["count1"])
        ])
        result = prdd.privacy_id_count(privacy_id_count_params)
        self.assertEqual([(0, "count0"), (1, "count1")], result.collect())

    @classmethod
    def tearDownClass(cls):
        cls.sc.stop()


if __name__ == '__main__':
    unittest.main()
