import pandas as pd
import base_function
import time
from datetime import date
from datetime import datetime
from dateutil.relativedelta import relativedelta
import yfinance as yf

yf.pdr_override()


class SAA_Permanent:
    """
    stock: 25% (VTI 미국 전체 주식)
    bond: 25% (TLT 미국 장기체)
    cash or short-term bond 25%, 단기채(SHY 미 단기체)
    gold 25% (GLD)
    monthly/quarterly/yearly rebalance
    """

    def __init__(self, trade_start_d=None, trade_end_d=None, lookback_period=None, period="month"):
        if trade_start_d is None:  # trade_start_d가 지정되어 있지 않을 때는 오늘 날짜로
            trade_start_d = str(date.today().strftime('%Y-%m-%d'))

        if time.strptime(trade_start_d, '%Y-%m-%d') < time.strptime('2001-05-24', '%Y-%m-%d'):
            print('Start Date out of bounds: must be after 2001-05-24')
            exit()

        else:
            self.universe = ['VITSX', 'TLT', 'GLD']

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

        self.cash = ['SHY']

    def execute(self):
        print('SAA_Permanent running')

        all_universe = self.universe + self.cash
        universe_df = base_function.get_adj_close_data(all_universe, self.date_start_d)

        monthly_universe_df = base_function.get_rebalancing_date(universe_df, period)

        month_cum_return, month_day_return = month_portfolio_result = \
            base_function.get_rebalanced_portfolio_result(universe_df)
        month_cagr, month_dd, month_mdd = base_function.get_evaluation(month_cum_return)

        quarter_cum_return, quarter_day_return = quarter_portfolio_result = \
            base_function.get_rebalanced_portfolio_result(universe_df, period="quarter")
        quarter_cagr, quarter_dd, quarter_mdd = base_function.get_evaluation(quarter_cum_return)

        year_cum_return, year_day_return = year_portfolio_result = \
            base_function.get_rebalanced_portfolio_result(universe_df)
        year_cagr, year_dd, year_mdd = base_function.get_evaluation(year_cum_return)

        return month_cagr, month_dd, month_mdd, quarter_cagr, quarter_dd, quarter_mdd, year_cagr, year_dd, year_mdd


"""
analyze)
permanent portfolio -> 월별, 분기별, 년별로 cagr, dd, mdd 차이 많이 없음
TC 비용 적은 yearly 택!!
"""
if __name__ == "__main__":
    start_date = "2005-05-24"
    end_date = "2023-01-10"
    period = "monthly"  # Recommended: monthly, quarterly, yearly

    saa_permanent = SAA_Permanent(trade_start_d=start_date, trade_end_d=end_date)

    month_cagr, month_dd, month_mdd, \
    quarter_cagr, quarter_dd, quarter_mdd, \
    year_cagr, year_dd, year_mdd = saa_permanent.execute()
