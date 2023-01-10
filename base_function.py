from pandas_datareader import data as pdr  # TODO. Use bloomberg terminal data instead
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt


def get_adj_close_data(ticker, data_sd, ed=None):
    extend_sd = str((datetime.strptime(data_sd, '%Y-%m-%d') - relativedelta(days=5)).date())  # 5 days earlier
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


def get_day_return(adj_close_data):     # 단일 종목의 일간 수익률
    day_return_df = adj_close_data / adj_close_data.shift(1).fillna(1)

    return day_return_df


def get_cum_return(adj_close_data):     # 단일 종목 누적 수익률
    cum_return_df = adj_close_data / adj_close_data.iloc[0]

    return cum_return_df


def get_portfolio_result(adj_close_data, weight=None):
    day_return = get_day_return(adj_close_data)  # 개별종목
    cum_return = get_cum_return(adj_close_data)  # 개별종목
    if not weight:  # 기본값 : 동일비중
        weight = [1 / len(adj_close_data.columns)] * len(adj_close_data.columns)
        print(f'weight: {weight}')
    portfolio_cum_return = (weight * cum_return).sum(axis=1)  # portfolio 누적 수익률
    portfolio_day_return = (portfolio_cum_return / portfolio_cum_return.shift(1)).fillna(1)  # portfolio 일별 수익률

    return portfolio_day_return, portfolio_cum_return


'''
get evaluation(투자성과지표)
CAGR(연평균 수익률) : Compound Annual Growth Rate
MDD(최대 낙폭) : Max DrawDown
'''


def get_evaluation(cum_return):
    cagr = cum_return.iloc[-1] ** (252 / len(cum_return))  # 기하평균 사용(곱의 평균)
    dd = (cum_return.cummax() - cum_return) / cum_return.cummax() * 100
    mdd = dd.max()

    print(f'최종 수익률: {cum_return.iloc[-1]}\ncagr: {cagr}\nmdd: {mdd}')

    return cagr, dd, mdd


def plot(adj_close_set):
    normalized_adj_close_set = (adj_close_set - adj_close_set.mean()) / adj_close_set.std()  # 데이터 정규화
    plt.figure(figsize=(12, 5))
    normalized_adj_close_set['SPY'].plot(label='STOCK')
    normalized_adj_close_set['IEF'].plot(label='BOND')
    plt.legend()
    plt.show()


def get_rebalancing_date(adj_close_data, period='month'):
    data = adj_close_data.copy()  # deep copy
    data = pd.DataFrame(data)
    data.index = pd.to_datetime(data.index)
    data['year'] = data.index.year
    data['month'] = data.index.month
    rebalancing_date = None

    if period == "month":
        rebalancing_date = data.drop_duplicates(['year', 'month'], keep="last").index

    if period == "quarter":
        quarter = [3, 6, 9, 12]  # 3,6,9,12월 말에 리밸런싱
        data = data.loc[data['month'].isin(quarter)]
        rebalancing_date = data.drop_duplicates(['year', 'month'], keep="last").index

    if period == "year":
        rebalancing_date = data.drop_duplicates(['year'], keep="last").index

    return rebalancing_date


'''
1. 자산별 비중이 없는 경우, 동일 비중 부과
2. 자산별 비중이 있는 경우, 차등 비중 부과
3. 단) adj_close_data와 weight_df.index(date)의 시점이 다를 수 있으므로, 
    adj_close_data의 시작일을 weight_df.index의 첫날로 맞추어 줘야 함
    i.e) adj_close_data의 시작일은 1월, weight_df의 시작일은 3월 => 날짜 gap이 생기므로 adj_close_data의 시작일을 3월로 설정
'''


def get_rebalanced_portfolio_result(adj_close_data, period="month", weight_df=None):
    if weight_df is None:       # 자산별 비중이 없는 경우, 동일 비중 부과
        rebalancing_date = get_rebalancing_date(adj_close_data, period)
        weight_df = pd.DataFrame(
            [[1 / len(adj_close_data.columns)] * len(adj_close_data.columns)] * len(rebalancing_date),
            index=rebalancing_date, columns=adj_close_data.columns)     # [1/n, 1/n ...]
    else:       # 자산별 비중이 없는 경우, 차등 비중 부과
        adj_close_data = adj_close_data.loc[weight_df.index[0]:]        # 시점 맞춰주기
        rebalancing_date = get_rebalancing_date(adj_close_data, period)

    portfolio_df = pd.DataFrame()      # 빈 데이터 프레임 생성

    start = rebalancing_date[0]     # 리밸런싱 날짜, 초기값 첫 투자일
    total_asset = 1     # 총 자산, 초기값 1 (투자 결과 연속 반영)

    for end in rebalancing_date[1:]:
        weight = weight_df.loc[start]       # 당월 리밸런싱 비율
        price_df = adj_close_data.loc[start:end]        # 당일 가격 데이터 (리밸런싱 period 사이의 데이터 가져오기)
        cum_return_df = get_cum_return(price_df)        # 당월 누적 수익률
        weighted_cum_return_df = weight * cum_return_df     # 당월말 리밸런싱 비율이 반영된 누적 수익률 (리밸런싱 비중 * 누적수익률)

        net_cum_return = total_asset * weighted_cum_return_df   # 전월 투자 결과 반영 (투자 결과 연속 반영)

        start = end     # start 갱신 (새로운 리밸런싱 period 얻기 위함)

        #print("갱신 전 총 자산: ", total_asset)
        total_asset = net_cum_return.iloc[-1].sum()     # 총 자산 갱신 (누적수익률)
        #print(net_cum_return)
        #print("갱신 후 총 자산: ", total_asset)

        portfolio_df = pd.concat([portfolio_df, net_cum_return])

    portfolio_df = portfolio_df.loc[~portfolio_df.index.duplicated(keep='last')]    # 리밸런싱 일자(매월 말) 중복 데이터 제거, duplicated 이면 true
    portfolio_cum_return = portfolio_df.sum(axis=1)     # portfolio 누적 수익률
    portfolio_day_return = (portfolio_cum_return / portfolio_cum_return.shift(1)).fillna(1)    #portfolio 일간 수익률

    return portfolio_cum_return, portfolio_day_return


'''
평균 모멘텀 스코어를 기반으로 한 투자 비중 구하기
n : 모멘텀 기간 1~n
nth Momentum : 현재 가격 / n개월 전 가격
return : 투자비중 weight_df, 평균 모멘텀 스코어 df
'''


def get_weight_by_momentum_score(adj_close_data, n=12):     # 1년 default
    avg_momentum_score = 0      # 평모스 초기값
    price_on_rebal_date = adj_close_data.loc[get_rebalancing_date(adj_close_data)]      # 리밸런싱 일자의 가격 데이터

    # 1~n개월 모멘텀 스코어 합 (n개월 평균 모멘텀 스코어)
    for i in range(1, n+1):
        avg_momentum_score = np.where(price_on_rebal_date / price_on_rebal_date.shift(i) > 1, 1, 0) + avg_momentum_score

    # 평모스 계산
    avg_momentum_score = pd.DataFrame(avg_momentum_score, index=price_on_rebal_date.index)
    avg_momentum_score = avg_momentum_score / n

    # 모멘텀 스코어에 따른 weight 계산
    weight_df = avg_momentum_score.divide(avg_momentum_score.sum(axis=1), axis=0).fillna(0)
    # 투자 비중이 모두 0인 구간에서는 현금 보유
    weight_df['cash'] = np.where(weight_df.sum(axis=1) == 0, 1, 0)

    # 투자비중, 평모스 리턴
    return weight_df, avg_momentum_score

