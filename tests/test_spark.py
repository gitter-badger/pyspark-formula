import logging
import random
import unittest
from itertools import product

import pandas as pd
from pyspark.sql import SparkSession

from ydot.spark import get_profile, get_columns, smatrices


class PySparkTest(unittest.TestCase):
    """
    PySpark test class.
    """

    @classmethod
    def supress_py4j_logging(cls):
        """
        Supresses p4j logging.

        :return: None.
        """
        logger = logging.getLogger('py4j')
        logger.setLevel(logging.WARN)

    @classmethod
    def create_pyspark_session(cls):
        """
        Creates a PySpark session.

        :return: PySpark session.
        """
        return (SparkSession.builder
                .master('local[4]')
                .appName('local-testing-pyspark')
                .getOrCreate())

    @classmethod
    def setUpClass(cls):
        """
        Sets up the class.

        :return: None.
        """
        cls.supress_py4j_logging()
        cls.spark = cls.create_pyspark_session()
        random.seed(37)

    @classmethod
    def tearDownClass(cls):
        """
        Tears down the class.

        :return: None.
        """
        cls.spark.stop()

    @staticmethod
    def _get_profile():
        """
        Gets the profile of a dataset.

        :return: Dictionary.
        """
        profile = {
            'a': ['left', 'right'],
            'b': ['high', 'mid', 'low'],
            'x1': [20.0],
            'x2': [3.0],
            'y': [1.0]
        }
        return profile

    @staticmethod
    def _get_pdf():
        """
        Gets a Pandas dataframe based on made-up profile.

        :return: Pandas dataframe.
        """
        profile = PySparkTest._get_profile()
        data = product(*(v for _, v in profile.items()))
        columns = [k for k, _ in profile.items()]
        df = pd.DataFrame(data, columns=columns)

        return df

    def _get_sdf(self):
        """
        Gets a Spark dataframe based on made-up profile.

        :return: Spark dataframe.
        """
        pdf = PySparkTest._get_pdf()
        sdf = self.spark.createDataFrame(pdf)
        return sdf


class SparkTest(PySparkTest):
    """
    Tests Spark operations.
    """

    def test_get_profile(self):
        """
        Tests getting profile of a Spark dataframe.

        :return: None.
        """
        sdf = self._get_sdf()
        sdf.printSchema()
        observed = get_profile(sdf)
        expected = {'b': ['mid', 'low', 'high'], 'a': ['right', 'left'], 'x1': [1.0], 'x2': [1.0], 'y': [1.0]}

        for k, lhs_vals in expected.items():
            assert k in observed
            rhs_vals = observed[k]

            assert len(lhs_vals) == len(rhs_vals)
            for v in lhs_vals:
                assert v in rhs_vals

    def test_get_columns_simple_formula_with_profile(self):
        """
        Tests get columns (simple) with profile specified.

        :return: None.
        """
        formula = "y ~ x1 + x2 + C(a,levels=profile['a']) + C(b, levels=profile['b'])"
        sdf = self._get_sdf()
        profile = {'b': ['mid', 'low', 'high'],
                   'a': ['right', 'left'],
                   'x1': [1.0],
                   'x2': [1.0],
                   'y': [1.0]}

        y_observed, X_observed = get_columns(formula, sdf, profile=profile)

        y_expected = ['y']
        X_expected = ['Intercept',
                      "C(a, levels=profile['a'])[T.left]",
                      "C(b, levels=profile['b'])[T.low]",
                      "C(b, levels=profile['b'])[T.high]",
                      'x1',
                      'x2']

        assert len(y_observed) == len(y_expected)
        assert len(X_observed) == len(X_expected)

        for y in y_observed:
            assert y in y_expected

        for x in X_observed:
            assert x in X_expected

    def test_get_columns_simple_formula_no_profile(self):
        """
        Tests get columns (simple) without a profile specified.

        :return: None.
        """
        formula = "y ~ x1 + x2 + C(a,levels=profile['a']) + C(b, levels=profile['b'])"
        sdf = self._get_sdf()

        y_observed, X_observed = get_columns(formula, sdf)

        y_expected = ['y']
        X_expected = ['Intercept',
                      "C(a, levels=profile['a'])[T.left]",
                      "C(b, levels=profile['b'])[T.low]",
                      "C(b, levels=profile['b'])[T.high]",
                      'x1',
                      'x2']

        assert len(y_observed) == len(y_expected)
        assert len(X_observed) == len(X_expected)

        for y in y_observed:
            assert y in y_expected

        for x in X_observed:
            assert x in X_expected

    def test_get_columns_variety_with_profile(self):
        """
        Tests a variety of formulas with profile.

        :return: None.
        """
        f1 = "y ~ x1 + x2 + C(a,levels=profile['a']) + C(b, levels=profile['b'])"
        f2 = "y ~ (x1 + x2 + C(a,levels=profile['a']) + C(b, levels=profile['b']))**2"
        f3 = "y ~ x1:x2 + C(a,levels=profile['a']):C(b, levels=profile['b'])"
        f4 = "y ~ x1*x2 + C(a,levels=profile['a'])*C(b, levels=profile['b'])"
        f5 = "y ~ x1 + x2 + C(a,levels=profile['a']) + C(b, levels=profile['b']) - 1"
        f6 = "y ~ (x1 + x2) / (C(a,levels=profile['a']) + C(b, levels=profile['b']))"

        formulas = [f1, f2, f3, f4, f5, f6]

        sdf = self._get_sdf()
        profile = {'b': ['low', 'mid', 'high'],
                   'a': ['left', 'right'],
                   'x1': [1.0],
                   'x2': [1.0],
                   'y': [1.0]}

        yy = [
            ['y'],
            ['y'],
            ['y'],
            ['y'],
            ['y'],
            ['y']
        ]
        XX = [
            ['Intercept', "C(a, levels=profile['a'])[T.right]", "C(b, levels=profile['b'])[T.mid]",
             "C(b, levels=profile['b'])[T.high]", 'x1', 'x2'],
            ['Intercept', "C(a, levels=profile['a'])[T.right]", "C(b, levels=profile['b'])[T.mid]",
             "C(b, levels=profile['b'])[T.high]", "C(a, levels=profile['a'])[T.right]:C(b, levels=profile['b'])[T.mid]",
             "C(a, levels=profile['a'])[T.right]:C(b, levels=profile['b'])[T.high]", 'x1',
             "x1:C(a, levels=profile['a'])[T.right]", "x1:C(b, levels=profile['b'])[T.mid]",
             "x1:C(b, levels=profile['b'])[T.high]", 'x2', "x2:C(a, levels=profile['a'])[T.right]",
             "x2:C(b, levels=profile['b'])[T.mid]", "x2:C(b, levels=profile['b'])[T.high]", 'x1:x2'],
            ['Intercept', "C(b, levels=profile['b'])[T.mid]", "C(b, levels=profile['b'])[T.high]",
             "C(a, levels=profile['a'])[T.right]:C(b, levels=profile['b'])[low]",
             "C(a, levels=profile['a'])[T.right]:C(b, levels=profile['b'])[mid]",
             "C(a, levels=profile['a'])[T.right]:C(b, levels=profile['b'])[high]", 'x1:x2'],
            ['Intercept', "C(a, levels=profile['a'])[T.right]", "C(b, levels=profile['b'])[T.mid]",
             "C(b, levels=profile['b'])[T.high]", "C(a, levels=profile['a'])[T.right]:C(b, levels=profile['b'])[T.mid]",
             "C(a, levels=profile['a'])[T.right]:C(b, levels=profile['b'])[T.high]", 'x1', 'x2', 'x1:x2'],
            ["C(a, levels=profile['a'])[left]", "C(a, levels=profile['a'])[right]", "C(b, levels=profile['b'])[T.mid]",
             "C(b, levels=profile['b'])[T.high]", 'x1', 'x2'],
            ['Intercept', 'x1', 'x2', "x1:x2:C(a, levels=profile['a'])[left]", "x1:x2:C(a, levels=profile['a'])[right]",
             "x1:x2:C(b, levels=profile['b'])[T.mid]", "x1:x2:C(b, levels=profile['b'])[T.high]"]
        ]

        for i, formula in enumerate(formulas):
            y_observed, X_observed = get_columns(formula, sdf, profile=profile)
            y_expected, X_expected = yy[i], XX[i]

            # print(f'{i}: {formula}')
            # print(y_observed)
            # print(X_observed)
            # print('-' * 15)

            assert len(y_observed) == len(y_expected)
            assert len(X_observed) == len(X_expected)

            for y in y_observed:
                assert y in y_expected

            for x in X_observed:
                assert x in X_expected

    def test_get_columns_variety_no_profile(self):
        """
        Tests a variety of formulas without profile.

        :return: None.
        """
        f1 = "y ~ x1 + x2 + a + b"
        f2 = "y ~ (x1 + x2 + a + b)**2"
        f3 = "y ~ x1:x2 + a:b"
        f4 = "y ~ x1*x2 + a*b"
        f5 = "y ~ x1 + x2 + a + b - 1"
        f6 = "y ~ (x1 + x2) / (a + b)"

        formulas = [f1, f2, f3, f4, f5, f6]

        sdf = self._get_sdf()

        yy = [
            ['y'],
            ['y'],
            ['y'],
            ['y'],
            ['y'],
            ['y']
        ]
        XX = [
            ['Intercept', 'a[T.right]', 'b[T.low]', 'b[T.mid]', 'x1', 'x2'],
            ['Intercept', 'a[T.right]', 'b[T.low]', 'b[T.mid]', 'a[T.right]:b[T.low]', 'a[T.right]:b[T.mid]', 'x1',
             'x1:a[T.right]', 'x1:b[T.low]', 'x1:b[T.mid]', 'x2', 'x2:a[T.right]', 'x2:b[T.low]', 'x2:b[T.mid]',
             'x1:x2'],
            ['Intercept', 'b[T.low]', 'b[T.mid]', 'a[T.right]:b[high]', 'a[T.right]:b[low]', 'a[T.right]:b[mid]',
             'x1:x2'],
            ['Intercept', 'a[T.right]', 'b[T.low]', 'b[T.mid]', 'a[T.right]:b[T.low]', 'a[T.right]:b[T.mid]', 'x1',
             'x2', 'x1:x2'],
            ['a[left]', 'a[right]', 'b[T.low]', 'b[T.mid]', 'x1', 'x2'],
            ['Intercept', 'x1', 'x2', 'x1:x2:a[left]', 'x1:x2:a[right]', 'x1:x2:b[T.low]', 'x1:x2:b[T.mid]']
        ]

        for i, formula in enumerate(formulas):
            y_observed, X_observed = get_columns(formula, sdf)
            y_expected, X_expected = yy[i], XX[i]

            # print(f'{i}: {formula}')
            # print(y_observed)
            # print(X_observed)
            # print('-' * 15)

            assert len(y_observed) == len(y_expected)
            assert len(X_observed) == len(X_expected)

            for y in y_observed:
                assert y in y_expected

            for x in X_observed:
                assert x in X_expected

    def test_smatrices_simple(self):
        """
        Test simple smatrices.

        :return: None.
        """
        f = 'y ~ x1 + x2 + a + b'
        sdf = self._get_sdf()
        e_rows = sdf.count()

        y_expected = ['y']
        X_expected = ['Intercept', 'a[T.right]', 'b[T.low]', 'b[T.mid]', 'x1', 'x2']

        y, X = smatrices(f, sdf)
        y, X = y.toPandas(), X.toPandas()

        y_observed = list(y.columns)
        X_observed = list(X.columns)

        # print(y_observed)
        # print('~' * 15)
        # print(y)
        # print('=' * 15)
        #
        # print(X_observed)
        # print('~' * 20)
        # print(X)

        assert e_rows == y.shape[0]
        assert e_rows == X.shape[0]
        assert len(y_expected) == len(y_observed)
        assert len(X_expected) == len(X_observed)

        for v in y_expected:
            assert v in y_observed
        for v in X_expected:
            assert v in X_observed

    def test_smatrices_simple_drop_intercept(self):
        """
        Test simple smatrices dropping intercept. Note that dropping intercept creates a
        situation where the one-hot encoded variables are not dropped! Bug with patsy?

        :return: None.
        """
        f = 'y ~ x1 + x2 + a + b - 1'
        sdf = self._get_sdf()
        e_rows = sdf.count()

        y_expected = ['y']
        X_expected = ['a[left]', 'a[right]', 'b[T.low]', 'b[T.mid]', 'x1', 'x2']

        y, X = smatrices(f, sdf)
        y, X = y.toPandas(), X.toPandas()

        y_observed = list(y.columns)
        X_observed = list(X.columns)

        # print(y_observed)
        # print('~' * 15)
        # print(y)
        # print('=' * 15)
        #
        # print(X_observed)
        # print('~' * 20)
        # print(X)

        assert e_rows == y.shape[0]
        assert e_rows == X.shape[0]
        assert len(y_expected) == len(y_observed)
        assert len(X_expected) == len(X_observed)

        for v in y_expected:
            assert v in y_observed
        for v in X_expected:
            assert v in X_observed

    def test_smatrices_two_way(self):
        """
        Test smatrices with two-way interaction.

        :return: None.
        """
        f = 'y ~ (x1 + x2 + a + b)**2'
        sdf = self._get_sdf()
        e_rows = sdf.count()

        y_expected = ['y']
        X_expected = ['Intercept', 'a[T.right]', 'b[T.low]', 'b[T.mid]', 'a[T.right]:b[T.low]',
                      'a[T.right]:b[T.mid]', 'x1', 'x1:a[T.right]', 'x1:b[T.low]', 'x1:b[T.mid]',
                      'x2', 'x2:a[T.right]', 'x2:b[T.low]', 'x2:b[T.mid]', 'x1:x2']

        y, X = smatrices(f, sdf)
        y, X = y.toPandas(), X.toPandas()

        y_observed = list(y.columns)
        X_observed = list(X.columns)

        # print(y_observed)
        # print('~' * 15)
        # print(y)
        # print('=' * 15)
        #
        # print(X_observed)
        # print('~' * 20)
        # print(X)

        assert e_rows == y.shape[0]
        assert e_rows == X.shape[0]
        assert len(y_expected) == len(y_observed)
        assert len(X_expected) == len(X_observed)

        for v in y_expected:
            assert v in y_observed
        for v in X_expected:
            assert v in X_observed

    def test_smatrices_three_way(self):
        """
        Test smatrices with three-way interaction.

        :return: None.
        """
        f = 'y ~ (x1 + x2 + a + b)**3'
        sdf = self._get_sdf()
        e_rows = sdf.count()

        y_expected = ['y']
        X_expected = ['Intercept', 'a[T.right]', 'b[T.low]', 'b[T.mid]', 'a[T.right]:b[T.low]',
                      'a[T.right]:b[T.mid]', 'x1', 'x1:a[T.right]', 'x1:b[T.low]', 'x1:b[T.mid]',
                      'x1:a[T.right]:b[T.low]', 'x1:a[T.right]:b[T.mid]', 'x2', 'x2:a[T.right]',
                      'x2:b[T.low]', 'x2:b[T.mid]', 'x2:a[T.right]:b[T.low]', 'x2:a[T.right]:b[T.mid]',
                      'x1:x2', 'x1:x2:a[T.right]', 'x1:x2:b[T.low]', 'x1:x2:b[T.mid]']

        y, X = smatrices(f, sdf)
        y, X = y.toPandas(), X.toPandas()

        y_observed = list(y.columns)
        X_observed = list(X.columns)

        # print(y_observed)
        # print('~' * 15)
        # print(y)
        # print('=' * 15)
        #
        # print(X_observed)
        # print('~' * 20)
        # print(X)

        assert e_rows == y.shape[0]
        assert e_rows == X.shape[0]
        assert len(y_expected) == len(y_observed)
        assert len(X_expected) == len(X_observed)

        for v in y_expected:
            assert v in y_observed
        for v in X_expected:
            assert v in X_observed

    def test_smatrices_weird(self):
        """
        Test smatrices with weird interactions.

        :return: None.
        """
        f = 'np.sin(y) + y ~ np.abs(x1) + (x2 + a)**2 + (np.cos(x2) + b)**2'
        sdf = self._get_sdf()
        e_rows = sdf.count()

        y_expected = ['np.sin(y)', 'y']
        X_expected = ['Intercept', 'a[T.right]', 'b[T.low]', 'b[T.mid]', 'np.abs(x1)', 'x2',
                      'x2:a[T.right]', 'np.cos(x2)', 'np.cos(x2):b[T.low]', 'np.cos(x2):b[T.mid]']

        y, X = smatrices(f, sdf)
        y, X = y.toPandas(), X.toPandas()

        y_observed = list(y.columns)
        X_observed = list(X.columns)

        # print(y_observed)
        # print('~' * 15)
        # print(y)
        # print('=' * 15)
        #
        # print(X_observed)
        # print('~' * 20)
        # print(X)

        assert e_rows == y.shape[0]
        assert e_rows == X.shape[0]
        assert len(y_expected) == len(y_observed)
        assert len(X_expected) == len(X_observed)

        for v in y_expected:
            assert v in y_observed
        for v in X_expected:
            assert v in X_observed
