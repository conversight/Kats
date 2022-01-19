# Copyright (c) Facebook, Inc. and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# pyre-unsafe

# This file defines tests for the abstract Evaluator class

import re
import unittest
import unittest.mock as mock

import numpy as np
import pandas as pd
from kats.evaluation.evaluator import Evaluator, EvaluationObject
from kats.tests.test_backtester_dummy_data import (
    PROPHET_0_108_FCST_DUMMY_DATA,
)
from kats.utils.testing import error_funcs
from pandas.testing import assert_frame_equal

pd_ver = float(re.findall("([0-9]+\\.[0-9]+)\\..*", pd.__version__)[0])
np.random.seed(42)

# Constant Values
FCST_EVALUATION_ERRORS = pd.DataFrame(
    {  # Rounded to 6 decimals
        "mape": [0.007622],
        "smape": [0.007588],
        "mae": [3.361111],
        "mse": [12.916667],
        "rmse": [3.593976],
    }
)


class EvaluatorTest(unittest.TestCase):
    @classmethod
    @mock.patch.multiple(Evaluator, __abstractmethods__=set())
    def setUpClass(cls):
        cls.evaluator = Evaluator()

    def test_create_evaluation_run(self) -> None:
        self.evaluator.create_evaluation_run(run_name="valid_run")
        self.assertEqual(
            self.evaluator.runs["valid_run"],
            EvaluationObject(None, None, None, None, None),
        )

    def test_create_invalid_run(self) -> None:
        # Non string name
        with self.assertRaises(ValueError):
            # pyre-ignore[6]: Expected `str`
            self.evaluator.create_evaluation_run(run_name=2)

        # Duplicate
        self.evaluator.create_evaluation_run(run_name="duplicate_run")
        with self.assertRaises(ValueError):
            self.evaluator.create_evaluation_run(run_name="duplicate_run"),

    def test_delete_evaluation_run(self) -> None:
        self.evaluator.create_evaluation_run(run_name="delete_run")
        self.evaluator.delete_evaluation_run(run_name="delete_run")
        with self.assertRaises(KeyError):
            self.evaluator.runs["delete_run"]

    def test_delete_invalid_run(self) -> None:
        with self.assertRaises(ValueError):
            self.evaluator.delete_evaluation_run(run_name="delete_invalid_run")

    def test_get_evaluation_run(self):
        self.evaluator.create_evaluation_run(run_name="retrieve_run")
        self.assertEqual(
            self.evaluator.get_evaluation_run(run_name="retrieve_run"),
            EvaluationObject(None, None, None, None, None),
        )

    def test_get_invalid_evaluation_run(self) -> None:
        with self.assertRaises(ValueError):
            self.evaluator.get_evaluation_run(run_name="invalid_retrieve_run")

    def test_evaluate(self):
        # Set up data
        PROPHET_0_108_FCST_DUMMY_DATA["rand_fcst"] = (
            np.random.randint(1, 6, PROPHET_0_108_FCST_DUMMY_DATA.shape[0])
            + PROPHET_0_108_FCST_DUMMY_DATA["fcst"]
        )
        labels = np.asarray(PROPHET_0_108_FCST_DUMMY_DATA["fcst"])
        preds = np.asarray(PROPHET_0_108_FCST_DUMMY_DATA["rand_fcst"])

        # Set up error funcs
        errs = {}
        for error_name, error_func in error_funcs.items():
            if not error_name == "mase":
                errs[error_name] = error_func

        # Set up evaluator
        self.evaluator.create_evaluation_run(run_name="test_evaluate")
        self.evaluator.runs["test_evaluate"].preds = preds

        eval_res = self.evaluator.evaluate(
            run_name="test_evaluate", metric_to_func=errs, labels=labels
        )
        if pd_ver < 1.1:
            assert_frame_equal(
                eval_res,
                FCST_EVALUATION_ERRORS,
                check_exact=False,
                check_less_precise=4,
            )
        else:
            assert_frame_equal(
                eval_res, FCST_EVALUATION_ERRORS, check_exact=False, atol=0.5, rtol=0.2
            )