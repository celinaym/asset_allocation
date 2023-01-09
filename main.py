import pandas as pd
import base_function
import yfinance as yf
yf.pdr_override()


start_date = '2007-12-31'           # Recommended: '2007-02-25', '2007-12-25', '2008-07-25', '2009-12-25'
end_date = '2022-11-30'

'''
S&P500 = SPY
미국중기국채(7-10) = IEF
'''

SPY = base_function.get_adj_close_data('SPY',  start_date, end_date)
IEF = base_function.get_adj_close_data('IEF',  start_date, end_date)
adj_close_set = pd.concat([SPY, IEF], axis=1)
adj_close_set.columns = ['SPY', 'IEF']

if pd.isnull(adj_close_set).values.any():
    adj_close_set.dropna(inplace=True)

else:
    print(f'result dataframe: {adj_close_set}')

'''
compare stocks & bonds
'''
base_function.plot(adj_close_set)


'''
asset allocation
'''
portfolio_daily_return, portfolio_cum_return = base_function.get_portfolio_result(adj_close_set)
print(f'stock, bond 1:1 ratio: {portfolio_cum_return[-1]}')
portfolio_cagr, portfolio_dd, portfolio_mdd = base_function.get_evaluation(portfolio_cum_return)