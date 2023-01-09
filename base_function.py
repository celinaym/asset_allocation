from pandas_datareader import data as pdr       # TODO. Use bloomberg terminal data instead
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
'''
종가데이터
ticker : 종목 번호
start : 시작일
end : 마지막 날짜
return : 종목의 종가 데이터
'''

'''
종가 데이터
Calendar 작업과, start ~ end 까지 데이터 무조건 있게 만듦
'''


def get_adj_close_data(ticker, data_sd, ed=None):
    extend_sd = str((datetime.strptime(data_sd, '%Y-%m-%d') - relativedelta(days=5)).date())       # 5 days earlier
    universe_df = pdr.get_data_yahoo(ticker, extend_sd, ed)['Adj Close']
    if ed is None:
        calendar1 = pd.date_range(start=extend_sd, end=universe_df.index[-1])
        calendar2 = pd.date_range(start=data_sd, end=universe_df.index[-1])
    else:
        calendar1 = pd.date_range(start=extend_sd, end=ed)
        calendar2 = pd.date_range(start=data_sd, end=ed)
    universe_df = universe_df.reindex(calendar1)
    universe_df = universe_df.fillna(method='ffill')
    universe_df = universe_df.reindex(calendar2)

    return universe_df


'''
daily return for each ticker
closeDataSet : adj close data
return : daily return of adj close data
'''


def get_day_return(adj_close_data):
    day_return_df = adj_close_data / adj_close_data.shift(1).fillna(1)

    return day_return_df


'''
cumulative return for each ticker == flow of assets
closeDataSet : adj close data
return : cum return for adj close data
'''


def get_cum_return(adj_close_data):
    cum_return_df = adj_close_data / adj_close_data.iloc[0]

    return cum_return_df


'''
get portfolio result
weight : weight for each ticker(portfolio 개별 자산 비중)
return : portfolio daily_return, cum_return
'''


def get_portfolio_result(adj_close_data, weight=None):
    day_return = get_day_return(adj_close_data)     # 개별종목
    cum_return = get_cum_return(adj_close_data)     # 개별종목
    if not weight:      # 기본값 : 동일비중
        weight = [1/len(adj_close_data.columns)] * len(adj_close_data.columns)
        print(f'weight: {weight}')
    portfolio_cum_return = (weight * cum_return).sum(axis=1)    # portfolio 누적 수익률
    portfolio_day_return = (portfolio_cum_return / portfolio_cum_return.shift(1)).fillna(1)     # portfolio 일별 수익률

    return portfolio_day_return, portfolio_cum_return


'''
get evaluation
CAGR(연평균 수익률) : Compound Annual Growth Rate
MDD(최대 낙폭) : Max DrawDown
'''


def get_evaluation(cum_return):
    cagr = cum_return.iloc[-1] ** (252 / len(cum_return))      # 기하평균 사용(곱의 평균)
    dd = (cum_return.cummax() - cum_return) / cum_return.cummax() * 100
    mdd = dd.max()

    print(f'최종 수익률: {cum_return.iloc[-1]}\ncagr: {cagr}\nmdd: {mdd}')

    return cagr, dd, mdd


def plot(adj_close_set):
    normalized_adj_close_set = (adj_close_set - adj_close_set.mean()) / adj_close_set.std()     # 데이터 정규화
    plt.figure(figsize=(12, 5))
    normalized_adj_close_set['SPY'].plot(label='STOCK')
    normalized_adj_close_set['IEF'].plot(label='BOND')
    plt.legend()
    plt.show()
