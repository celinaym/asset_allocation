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
    IWM
    QQQ(나스닥)
    VGK(유럽 주식)
    EWJ(일본 주식)
    VWO(개발도상국 주식)
    VNQ(미국 리츠)
    GSG(원자재)
    GLD(금)
    TLT(미국 장기채)
    HYG(high yield bond)
    LQD(회사채)

    defensive universe:
    UST(미국 중기채 leverage) -> TLT(미국 장기국채)
    SHY(미국 단기국채)
    IEF(미국 중기국채)

    canary universe:
    VWO(개발도상국 주식)
    BND(미국 총채권)

    1. momentum_score = (현재 주가 / n개월 전 주가) - 1
    (최근 1개월 수익률 * 12) + (최근 3개월 수익률 * 4) + (최근 6개월 수익률 * 2) + (최근 12개월 수익률 * 1)
    2. all_canary universe momentum_score > 0 -> offensive top2
    3. canary universe 중 하나의 자산만 momentum_score > 0 -> offensive top1, defensive top1
    4. all_canary_universe momentum_score < 0 -> defensive all-in

    """

    def __init__(self, trade_start_d=None, trade_end_d=None, lookback_period=None, period="month"):
        if trade_start_d is None:  # trade_start_d가 지정되어 있지 않을 때는 오늘 날짜로
            trade_start_d = str(date.today().strftime('%Y-%m-%d'))

        if time.strptime(trade_start_d, '%Y-%m-%d') < time.strptime('2001-05-24', '%Y-%m-%d'):
            print('Start Date out of bounds: must be after 2001-05-24')
            exit()

        else:
            self.offensive_universe = ['SPY', 'IWM', 'QQQ', 'VGK', 'EWJ', 'VWO', 'VNQ', 'GSG', 'GLD', 'TLT', 'HYG', 'LQD']
            self.defensive_universe = ['SHY', 'IEF', 'TLT']
            self.canary_universe = ['VWO', 'BND']

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

        all_universe = self.offensive_universe + self.defensive_universe + self.canary_universe
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
        2. all_canary universe momentum_score > 0 -> offensive top2
        3. canary universe 중 하나의 자산만 momentum_score > 0 -> offensive top1, defensive top1
        4. all_canary_universe momentum_score < 0 -> defensive all-in
        """
        is_canary = (momentum_score[self.canary_universe] > 0).sum(axis=1)
        print("=====================is_canary====================")
        print(is_canary)
        weight_df = momentum_score.apply(self.get_weight, axis=1, args=(is_canary,))
        print("=============================weight_df===============================")
        print(weight_df)

        month_cum_return, month_day_return = month_portfolio_result = \
            base_function.get_rebalanced_portfolio_result(adj_close_data=universe_df, weight_df=weight_df)
        month_cagr, month_dd, month_mdd = base_function.get_evaluation(month_cum_return)

        quarter_cum_return, quarter_day_return = quarter_portfolio_result = \
            base_function.get_rebalanced_portfolio_result(universe_df, "quarter", weight_df)
        quarter_cagr, quarter_dd, quarter_mdd = base_function.get_evaluation(quarter_cum_return)

        year_cum_return, year_day_return = year_portfolio_result = \
            base_function.get_rebalanced_portfolio_result(universe_df, "year", weight_df)
        year_cagr, year_dd, year_mdd = base_function.get_evaluation(year_cum_return)

        return month_cagr, month_dd, month_mdd, quarter_cagr, quarter_dd, quarter_mdd, year_cagr, year_dd, year_mdd

    def get_weight(self, row, is_canary):

        if is_canary[row.name] == 2:
            # 카나리아 자산 모멘텀 스코어가 모두 0 초과일 때, offensive_universe 중 momentum_score가 가장 큰 2개 자산 보유
            offensive_top2 = row[self.offensive_universe].nlargest(n=2).index
            print('offensive_top2')
            print(offensive_top2)
            result = pd.Series(row.index.isin(offensive_top2), index=row.index, name=row.name).astype(int).replace(1, 0.5)      # 비중 절반씩
            return result

        elif is_canary[row.name] == 1:
            # 카나리아 자산 모멘텀 스코어가 모두 0 초과일 때, offensive_top1 & defensive_top1
            offensive_top1 = row[self.offensive_universe].idxmax()
            defensive_top1 = row[self.defensive_universe].idxmax()
            result = pd.Series(row.index.isin([offensive_top1, defensive_top1]), index=row.index, name=row.name).astype(int).replace(1, 0.5)
            return result

        else:
            # 카나리아 자산 모두 모멘텀 스코어가 0 이하라면 수비 자산 중 모멘텀 스코어가 가장 큰 자산에 올인
            defensive_top1 = row[self.defensive_universe].idxmax()
            result = pd.Series(row.index == defensive_top1, index=row.index, name=row.name).astype(int)
            return result


if __name__ == "__main__":
    start_date = "2005-05-24"
    end_date = "2023-01-10"
    period =  "month"  # Recommended: month, quarter, year

    daa_vaa = DAA_VAA(trade_start_d=start_date, trade_end_d=end_date)

    month_cagr, month_dd, month_mdd, \
    quarter_cagr, quarter_dd, quarter_mdd, \
    year_cagr, year_dd, year_mdd = daa_vaa.execute()