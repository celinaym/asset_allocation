import pandas as pd

import base_function
import time
from datetime import date
from datetime import datetime
from dateutil.relativedelta import relativedelta
import yfinance as yf
import numpy as np

yf.pdr_override()


class DAA_FAA:
    """
    VTI(미국 전체 주식)
    VEA(미국 제외 선진국 주식)
    VWO(전 세계 주식)
    BND(미국 전체 채권)
    SHY(미국 단기 국채)
    VNQ(미국 리츠)
    DBC(원자재)

    7개 자산의 cor, vol, momentum 고려한 TOP3 선정
    if momentum_score < 1 => cash

    momentum : 4개월 수익률 순위 (높을수록 good)
    vol : 4개월 일일 수익률 sd (낮을수록 good)
    cor : 4개월 하나의 자산과 다른 6개 자산간의 일일수익률의 correlation (낮을수록 good)
    (momentum * 1) + (vol * 0.5) + (cor * 0.5)이 낮은 순서대로 순위
    """

    def __init__(self, trade_start_d=None, trade_end_d=None, lookback_period=None, period="month"):
        if trade_start_d is None:  # trade_start_d가 지정되어 있지 않을 때는 오늘 날짜로
            trade_start_d = str(date.today().strftime('%Y-%m-%d'))

        if time.strptime(trade_start_d, '%Y-%m-%d') < time.strptime('2001-05-24', '%Y-%m-%d'):
            print('Start Date out of bounds: must be after 2001-05-24')
            exit()

        else:
            self.universe = ['VTISX', 'VEA', 'VWO', 'BND', 'SHY', 'VNQ', 'DBC']

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

        all_universe = self.universe
        universe_df = base_function.get_adj_close_data(all_universe, self.date_start_d)
        faa_rebal_date = base_function.get_rebalancing_date(universe_df, period)
        faa_rebal_df = universe_df.loc[faa_rebal_date]

        weight_df = self.get_weight(faa_rebal_date, faa_rebal_df, universe_df)

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

    def get_weight(self, faa_rebal_date, faa_rebal_df, universe_df):
        """
        momentum : 4개월 수익률
        volatility : 4개월 daily return sd
        correlation : 4개월 하나의 자산과 다른 6개 자산 간의 daily return correlation
        """

        print('===============FAA_Rebal_date==================')
        print(faa_rebal_date)     # 2005-05-31, 2005-06-30...

        # 1) momentum
        momentum_df = faa_rebal_df / faa_rebal_df.shift(4)
        momentum_df.dropna(inplace=True)
        momentum_rk = momentum_df.rank(method="max", axis=1, ascending=False)
        print('================momentum_rk===================')
        print(momentum_rk)      # 2016-07-31, 2016-08-31...

        # 2) volatility 3) correlation
        std4 = pd.DataFrame()       # returns class instance
        cor4 = pd.DataFrame()       # returns class instance
        reverse_rebal_date = faa_rebal_date[::-1]        # Re-balancing date in reverse order
        print('=================reverse_rebal_date=====================')
        print(reverse_rebal_date)

        day_return = base_function.get_day_return(universe_df)
        print('===================day_return================')
        print(day_return)

        for index, date in enumerate(reverse_rebal_date):
            if index >= len(reverse_rebal_date)-4:      # 4개월치 데이터가 없을 경우, break
                break

            before_4month = reverse_rebal_date[index+4]     # 4개월 전 시점
            std = day_return.loc[date:before_4month:-1].std()     # 4개월 daily_return std
            std.name = date
            std4 = std4.append(std)

            cor = day_return.loc[date:before_4month:-1].corr(method="pearson").sum(axis=1)-1    # 자신에 대한 상관계수를 제거하기 위해 -1
            cor.name = date
            cor4 = cor4.append(cor)

        std4_rank = std4.rank(method="first", axis=1, ascending=True)
        print('================std4_rank============')
        print(std4_rank)
        std4_rank = std4_rank.sort_index(ascending=True)

        cor4_rank = cor4.rank(method="first", axis=1, ascending=True)
        print('================cor4_rank============')
        print(cor4_rank)
        cor4_rank = cor4_rank.sort_index(ascending=True)

        # 가중평균
        total_weight = (momentum_rk + 0.5 * std4_rank + 0.5 * cor4_rank)
        total_weight.dropna(inplace=True)
        total_rank = total_weight.rank(method="first", axis=1, ascending=True)
        print('=================total rank=================')
        print(total_rank)

        weight = (total_rank <= 3) & (momentum_df >= 1)     # if momentum < 1 => cash
        faa_weight = weight.replace(True, 1/3).replace(False, 0)
        faa_weight['cash'] = 1 - faa_weight.sum(axis=1)
        print('====================faa_weight=================')
        print(faa_weight)

        return faa_weight


if __name__ == "__main__":
    start_date = "2005-05-24"
    end_date = "2023-01-10"
    period =  "month"  # Recommended: month, quarter, year

    daa_faa = DAA_FAA(trade_start_d=start_date, trade_end_d=end_date)

    month_cagr, month_dd, month_mdd, \
    quarter_cagr, quarter_dd, quarter_mdd, \
    year_cagr, year_dd, year_mdd = daa_faa.execute()