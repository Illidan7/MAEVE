# Data manipulation
import numpy as np
import pandas as pd

# Function to calculate Moving Averages of price
def movAvg(df, len):
    sum = 0

    for idx, row in df.iterrows():
        if(idx<len):
            sum += row['close']

    MA = sum/len

    return MA

# Scale for moving average trends (hourly)
# 8 MA - 10-20 Medium slope (0.2%), 30-50 Steep slope (0.5%), 60-90 Parabolic (0.8%)
# 55 MA - 15-25 Steep slope (0.2%)
# 100 MA - >5 Slope, <5 sideways
def movAvgTrend(df, length, trendlength=5):
    MAhist = []
    for x in range(trendlength):
        MAhist.append(movAvg(df[x:].reset_index(),length))

    print(MAhist)
    trend = MAhist[0] - MAhist[trendlength-1]
    trend = trend/(trendlength-1)

    return trend


# def trendShift(list):
#     signs = []
#     count=0
#     prev = None
#     for item in list:
#         signs.append(np.sign(item))
#
#     for sign in signs:
#         if prev is None:
#             prev=sign
#             count=1
#         if sign == prev:
#             count+=1
#         else:
#             count=1
#
#     if count < 10:
#
