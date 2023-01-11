import pandas as pd

import base_function
import time
from datetime import date
from datetime import datetime
from dateutil.relativedelta import relativedelta
import yfinance as yf
import numpy as np

yf.pdr_override()


class DAA_VAA:
    """
    offensive, defensive

    offensive universe:
    SPY(미국 주식)
    VEA(선진국 주식)
    EEM(개도국 주식)
    AGG(미국 총채권)

    defensive universe:
    LQD(미국 회사채)
    SHY(미국 단기국채)
    IEF(미국 중기국채)

    1. momentum_score = (현재 주가 / n개월 전 주가) - 1
    (최근 1개월 수익률 * 12) + (최근 3개월 수익률 * 4) + (최근 6개월 수익률 * 2) + (최근 12개월 수익률 * 1)
    2. if all_offensive4 > 0 => select offensive ticker w/t greatest momentum
    3. if one_offensive4 < 0 => select defensive ticker w/t greatest momentum

    """

    def __init__(self, trade_start_d=None, trade_end_d=None, lookback_period=None, period="month"):
        if trade_start_d is None:  # trade_start_d가 지정되어 있지 않을 때는 오늘 날짜로
            trade_start_d = str(date.today().strftime('%Y-%m-%d'))

        if time.strptime(trade_start_d, '%Y-%m-%d') < time.strptime('2001-05-24', '%Y-%m-%d'):
            print('Start Date out of bounds: must be after 2001-05-24')
            exit()

        else:
            self.offensive_universe = ['SPY', 'VEA', 'EEM', 'AGG']
            self.defensive_universe = ['LQD', 'SHY', 'IEF']

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
        print('DAA_FAA running')

        all_universe = self.offensive_universe + self.defensive_universe
        universe_df = base_function.get_adj_close_data(all_universe, self.date_start_d)
        vaa_rebal_date = base_function.get_rebalancing_date(universe_df, period)
        vaa_rebal_df = universe_df.loc[vaa_rebal_date]

        momentum1 = vaa_rebal_df / vaa_rebal_df.shift(1) - 1   # 1개월
        momentum3 = vaa_rebal_df / vaa_rebal_df.shift(3) - 1   # 3개월
        momentum6 = vaa_rebal_df / vaa_rebal_df.shift(6) - 1   # 6개월
        momentum12 = vaa_rebal_df / vaa_rebal_df.shift(12) - 1 # 12개월

        momentum_score = momentum1 * 12 + momentum3 * 4 + momentum6 * 2 + momentum12 * 1
        momentum_score.dropna(inplace=True)

        print('===================momentum_score==================')
        print(momentum_score)

        """
        if all_offensive4 > 0 => select offensive ticker w/t greatest momentum
        if one_offensive4 < 0 => select defensive ticker w/t greatest momentum
        """
        is_offensive = (momentum_score[self.offensive_universe] > 0).all(axis=1)    # 모든 값이 True인가
        print("=====================is_offensive====================")
        print(is_offensive)
        weight_df = momentum_score.apply(self.get_weight, axis=1, args=(is_offensive,))
        print("======================momentum_score==========================")
        print(momentum_score)

        # cash 추가
        universe_df_with_cash = universe_df.copy()
        universe_df_with_cash.loc[:, 'cash'] = 1
        print('===================universe_df_with_cash=======================')
        print(universe_df_with_cash)

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

    def get_weight(self, row, is_offensive):

        print('row.name', row.name)     # date
        print('row.index', row.index)   # ticker name

        if is_offensive[row.name]:      # is_offensive의 값이 true라면 -> 공격형 자산 투자
            """
            row[self.offensive_universe.idmax()] => 공격형 자산 중 모멘텀 스코어가 가장 높은 종목명(ex: SPY)
            row.index = 모든 종목명 [SPY, VEA, EEM ...]
            row.index == row[self.offensive_universe].idmax() => [True, False, False...]
            """
            result = pd.Series(row.index == row[self.offensive_universe].idxmax(), index=row.index, name=row.name).astype(int)
            return result

        result = pd.Series(row.index == row[self.defensive_universe].idxmax(), index=row.index, name=row.name).astype(int)
        return result


if __name__ == "__main__":
    start_date = "2005-05-24"
    end_date = "2023-01-10"
    period =  "month"  # Recommended: month, quarter, year

    daa_vaa = DAA_VAA(trade_start_d=start_date, trade_end_d=end_date)

    month_cagr, month_dd, month_mdd, \
    quarter_cagr, quarter_dd, quarter_mdd, \
    year_cagr, year_dd, year_mdd = daa_vaa.execute()