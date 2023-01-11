import pandas as pd

import base_function
import time
from datetime import date
from datetime import datetime
from dateutil.relativedelta import relativedelta
import yfinance as yf
import numpy as np

yf.pdr_override()


class DAA_GTAA:
    """
    stock 20% (SPY)
    EFA(선진국 주식) 20%
    IEF(미국 중기 채권) 20%
    DBC(원자재) 20%
    VNQ(미국 리츠) 20% - Real Estate
    monthly/quarterly/yearly rebalance

    Momentum score = (가격 / 200일 이동 평균선)-1
    if momentum_score < 0, then cash
    """

    def __init__(self, trade_start_d=None, trade_end_d=None, lookback_period=None, period="month"):
        if trade_start_d is None:  # trade_start_d가 지정되어 있지 않을 때는 오늘 날짜로
            trade_start_d = str(date.today().strftime('%Y-%m-%d'))

        if time.strptime(trade_start_d, '%Y-%m-%d') < time.strptime('2001-05-24', '%Y-%m-%d'):
            print('Start Date out of bounds: must be after 2001-05-24')
            exit()

        else:
            self.universe = ['SPY', 'EFA', 'IEF', 'DBC', 'VNQ']

        if lookback_period is None:
            date_start_d = trade_start_d

        else:
            date_start_d = str(
                (datetime.strptime(trade_start_d, '%Y-%m-%d') - relativedelta(months=lookback_period)).date())

        self.date_start_d = date_start_d
        self.trade_start_d = trade_start_d
        self.trade_end_d = trade_end_d
        self.lookback_period = lookback_period
        self.period = period

    def execute(self):
        print('DAA_GTAA running')

        all_universe = self.universe
        universe_df = base_function.get_adj_close_data(all_universe, self.date_start_d)

        universe_df_with_cash = universe_df.copy()
        universe_df_with_cash.loc[:, 'cash'] = 1
        print('==================universe_df_with_cash=================')
        print(universe_df_with_cash)

        monthly_universe_df = base_function.get_rebalancing_date(universe_df_with_cash, period)
        weight_df = self.get_weight(monthly_universe_df, universe_df)

        month_cum_return, month_day_return = month_portfolio_result = \
            base_function.get_rebalanced_portfolio_result(adj_close_data=universe_df_with_cash, weight_df=weight_df)
        month_cagr, month_dd, month_mdd = base_function.get_evaluation(month_cum_return)

        quarter_cum_return, quarter_day_return = quarter_portfolio_result = \
            base_function.get_rebalanced_portfolio_result(universe_df_with_cash, "quarter", weight_df)
        quarter_cagr, quarter_dd, quarter_mdd = base_function.get_evaluation(quarter_cum_return)

        year_cum_return, year_day_return = year_portfolio_result = \
            base_function.get_rebalanced_portfolio_result(universe_df_with_cash, "year", weight_df)
        year_cagr, year_dd, year_mdd = base_function.get_evaluation(year_cum_return)

        return month_cagr, month_dd, month_mdd, quarter_cagr, quarter_dd, quarter_mdd, year_cagr, year_dd, year_mdd

    def get_weight(self, monthly_universe_df, universe_df):
        """
        :param monthly_universe_df: rebalanced date
        :param universe_df:
        :return:

        5개 자산에 각 20% 비중으로 투자하되, 모멘텀 스코어 0 미만인 자산의 비중만큼은 현금 보유
        """
        print('monthly_universe_df')
        print(monthly_universe_df)      # 2005-05-31, 2005-06-30, 2005-07-31...

        ma_200 = universe_df.rolling(window=200).mean()     # 200 days moving average
        momentum_score = (universe_df / ma_200) - 1
        momentum_score.dropna(inplace=True)
        print('=====================momentum_score====================')
        print(momentum_score)       # 2006-08-24, 2006-08-25, ...

        weight_df = pd.DataFrame(np.where(momentum_score > 0, 0.2, 0),
                                 index=momentum_score.index, columns=universe_df.columns)
        print(weight_df)
        weight_df = weight_df.loc[momentum_score.index[0:]]     # 시점 맞추기
        print('=====================weight_df=====================')
        print(weight_df)

        weight_df['cash'] = 1 - weight_df.sum(axis=1)
        print('weight_df_cash')
        print(weight_df)

        return weight_df


"""
analyze)
all weather portfolio -> 월별, 분기별, 년별로 cagr, dd, mdd 차이 많이 없음
TC 비용 적은 yearly 택
"""
if __name__ == "__main__":
    start_date = "2005-05-24"
    end_date = "2023-01-10"
    period =  "month"  # Recommended: month, quarter, year

    daa_gtaa = DAA_GTAA(trade_start_d=start_date, trade_end_d=end_date)

    month_cagr, month_dd, month_mdd, \
    quarter_cagr, quarter_dd, quarter_mdd, \
    year_cagr, year_dd, year_mdd = daa_gtaa.execute()