#!/usr/bin/env python3

# Copyright (c) Facebook, Inc. and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from typing import Tuple

import infrastrategy.kats.models.model as m
import numpy as np
import pandas as pd
from infrastrategy.kats.consts import Params, TimeSeriesData
from statsmodels.tsa.statespace.sarimax import SARIMAX
from typing import List, Dict
from infrastrategy.kats.utils.parameter_tuning_utils import (
    get_default_sarima_parameter_search_space
)


class SARIMAParams(Params):
    __slots__ = ["p", "d", "q"]

    def __init__(
        self,
        p: int,
        d: int,
        q: int,
        exog=None,
        seasonal_order: Tuple = (0, 0, 0, 0),
        trend=None,
        measurement_error: bool = False,
        time_varying_regression: bool = False,
        mle_regression: bool = True,
        simple_differencing: bool = False,
        enforce_stationarity: bool = True,
        enforce_invertibility: bool = True,
        hamilton_representation: bool = False,
        concentrate_scale: bool = False,
        trend_offset: int = 1,
        use_exact_diffuse: bool = False,
        **kwargs
    ) -> None:
        super().__init__()
        self.p = p
        self.d = d
        self.q = q
        self.exog = exog
        self.seasonal_order = seasonal_order
        self.trend = trend
        self.measurement_error = measurement_error
        self.time_varying_regression = time_varying_regression
        self.mle_regression = mle_regression
        self.simple_differencing = simple_differencing
        self.enforce_stationarity = enforce_stationarity
        self.enforce_invertibility = enforce_invertibility
        self.hamilton_representation = hamilton_representation
        self.concentrate_scale = concentrate_scale
        self.trend_offset = trend_offset
        self.use_exact_diffuse = use_exact_diffuse
        logging.debug(
            "Initialized SARIMAParams with parameters. "
            "p:{p}, d:{d}, q:{q},seasonal_order:{seasonal_order}".format(
                p=p, d=d, q=q, seasonal_order=seasonal_order
            )
        )

    def validate_params(self):
        logging.info("Method validate_params() is not implemented.")
        pass


class SARIMAModel(m.Model):
    def __init__(self, data: TimeSeriesData, params: SARIMAParams, ) -> None:
        super().__init__(data, params)
        if not isinstance(self.data.value, pd.Series):
            msg = "Only support univariate time series, but get {type}.".format(
                type=type(self.data.value)
            )
            logging.error(msg)
            raise ValueError(msg)

    def fit(self,
            start_params=None,
            transformed=None,
            includes_fixed=None,
            cov_type=None,
            cov_kwds=None,
            method="lbfgs",
            maxiter=50,
            full_output=1,
            disp=False,
            callback=None,
            return_params=False,
            optim_score=None,
            optim_complex_step=None,
            optim_hessian=None,
            flags=None,
            low_memory=False,
            ) -> None:
        logging.debug("Call fit() method")
        self.start_params = start_params
        self.transformed = transformed
        self.includes_fixed = includes_fixed
        self.cov_type = cov_type
        self.cov_kwds = cov_kwds
        self.method = method
        self.maxiter = maxiter
        self.full_output = full_output
        self.disp = disp
        self.callback = callback
        self.return_params = return_params
        self.optim_score = optim_score
        self.optim_complex_step = optim_complex_step
        self.optim_hessian = optim_hessian
        self.flags = flags
        self.low_memory = low_memory

        logging.info("Created SARIMA model.")
        sarima = SARIMAX(
            self.data.value,
            order=(self.params.p, self.params.d, self.params.q),
            exog=self.params.exog,
            seasonal_order=self.params.seasonal_order,
            trend=self.params.trend,
            measurement_error=self.params.measurement_error,
            time_varying_regression=self.params.time_varying_regression,
            mle_regression=self.params.mle_regression,
            simple_differencing=self.params.simple_differencing,
            enforce_stationarity=self.params.enforce_stationarity,
            enforce_invertibility=self.params.enforce_invertibility,
            hamilton_representation=self.params.hamilton_representation,
            concentrate_scale=self.params.concentrate_scale,
            trend_offset=self.params.trend_offset,
            use_exact_diffuse=self.params.use_exact_diffuse,
        )
        self.model = sarima.fit(
            start_params=self.start_params,
            transformed=self.transformed,
            includes_fixed=self.includes_fixed,
            cov_type=self.cov_type,
            cov_kwds=self.cov_kwds,
            method=self.method,
            maxiter=self.maxiter,
            full_output=self.full_output,
            disp=self.disp,
            callback=self.callback,
            return_params=self.return_params,
            optim_score=self.optim_score,
            optim_complex_step=self.optim_complex_step,
            optim_hessian=self.optim_hessian,
            flags=self.flags,
            low_memory=self.low_memory,
        )
        logging.info("Fitted SARIMA.")

    def predict(self, steps: int, include_history=False, **kwargs) -> pd.DataFrame:
        logging.debug("Call predict() with parameters. "
        "steps:{steps}, kwargs:{kwargs}".format(
            steps=steps, kwargs=kwargs
        ))
        self.include_history = include_history
        self.freq = kwargs.get("freq", pd.infer_freq(self.data.time))
        fcst = self.model.get_forecast(steps)

        logging.info("Generated forecast data from SARIMA model.")
        logging.debug("Forecast data: {fcst}".format(fcst=fcst))

        self.y_fcst = fcst.predicted_mean
        pred_interval = fcst.conf_int()
        if pred_interval.iloc[0, 0] < pred_interval.iloc[0, 1]:
            self.y_fcst_lower = np.array(pred_interval.iloc[:, 0])
            self.y_fcst_upper = np.array(pred_interval.iloc[:, 1])

        last_date = self.data.time.max()
        dates = pd.date_range(start=last_date, periods=steps + 1, freq=self.freq)

        self.dates = dates[dates != last_date]  # Return correct number of periods

        if include_history:
            # generate historical fit
            history_fcst = self.model.get_prediction(0)
            history_ci = history_fcst.conf_int()
            if ("lower" in history_ci.columns[0]) and ("upper" in history_ci.columns[1]):
                ci_lower_name, ci_upper_name = history_ci.columns[0], history_ci.columns[1]
            else:
                msg = "Error when getting prediction interval from statsmodels SARIMA API"
                logging.error(msg)
                raise ValueError(msg)
            self.fcst_df = pd.DataFrame(
                {
                    "time": np.concatenate((pd.to_datetime(self.data.time), self.dates)),
                    "fcst": np.concatenate((history_fcst.predicted_mean, self.y_fcst)),
                    "fcst_lower": np.concatenate((history_ci[ci_lower_name], self.y_fcst_lower)),
                    "fcst_upper": np.concatenate((history_ci[ci_upper_name], self.y_fcst_upper)),
                }
            )

            # the first k elements of the fcst and lower/upper are not legitmate
            # thus we need to assign np.nan to avoid confusion
            # k = max(p, d, q) + max(P, D, Q) * seasonal_order + 1
            k = max(self.params.p, self.params.d, self.params.q) \
                + max(self.params.seasonal_order[0:3]) * self.params.seasonal_order[3] + 1

            self.fcst_df.loc[0:k, ["fcst", "fcst_lower", "fcst_upper"]] = np.nan
        else:
            self.fcst_df = pd.DataFrame(
                {
                    "time": self.dates,
                    "fcst": self.y_fcst,
                    "fcst_lower": self.y_fcst_lower,
                    "fcst_upper": self.y_fcst_upper,
                }
            )

        logging.debug("Return forecast data: {fcst_df}".format(fcst_df=self.fcst_df))
        return self.fcst_df

    def plot(self):
        logging.info("Generating chart for forecast result from SARIMA model.")
        m.Model.plot(self.data, self.fcst_df, include_history=self.include_history)

    def __str__(self):
        return "SARIMA"

    @staticmethod
    def get_parameter_search_space() -> List[Dict[str, object]]:
        """
        Move the implementation of get_parameter_search_space() out of sarima
        to avoid the massive dependencies of sarima and huge build size.
        Check https://fburl.com/kg04hx5y for detail.
        """
        return get_default_sarima_parameter_search_space()