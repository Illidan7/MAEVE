# Data manipulation
import numpy as np
import pandas as pd
# Date time manipulation
import os
from datetime import datetime
import time
import logging
# Coinbase Pro python client
import cbpro
# Coinbase API request
import requests
import json



# Coinbase pro API credentials
key = '****'
b64secret = '****'
passphrase = '****'

# Initialize CoinbasePro API client
auth_client = cbpro.AuthenticatedClient(key, b64secret, passphrase)


def getCurrPrice():
    response = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot")
    data = response.json()
    currency = data["data"]["base"]
    price = data["data"]["amount"]
    logging.info(f"Currency : {currency}  Price: {price}")
    price = float(price)
    return price

def getBalance(wallet):
    accts = auth_client.get_accounts()
    need_acct = None
    for acct in accts:
        if acct['currency']== wallet:
            need_acct = acct
            break
    logging.info(need_acct['currency'] + ':' + need_acct['balance'])
    bal = need_acct['balance']
    bal = float(bal)
    return bal



# Function to return dataframe of historical hourly price data
def getPriceData(ticker, granularity):
    tckinpt = ticker + '-USD'
    hist_price = auth_client.get_product_historic_rates(tckinpt, granularity=granularity)
    df = pd.DataFrame(hist_price)
    df.columns = ['unixtime', 'low', 'high', 'open', 'close', 'volume']
    df['localtime'] = df.apply(lambda row : time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row['unixtime'])), axis=1)
    df['localtime'] = pd.to_datetime(df['localtime'])
    return df


# Function to buy BTC and set a stop loss
def marketBuy(orderAmt):
    # Place a market order by specifying amount of USD to use.
    # Alternatively, `size` could be used to specify quantity in BTC amount.
    order = auth_client.place_market_order(product_id='BTC-USD',
                               side='buy',
                               funds=orderAmt)
    # Store order id
    orderid = order['id']
    buyPrice = None
    conf = None

    # Check if order id has been filled
    while(True):

        buyPrice, buyFee, conf = orderFillConf(orderid)

        if conf == 1:
            break

    msg = "BUY placed for $" + str(orderAmt) + " of BTC @ $" + str(buyPrice)
    logging.info(msg)

    return buyPrice, buyFee


def marketSell(orderAmt):
    # Place a market order by specifying amount of USD to use.
    # Alternatively, `size` could be used to specify quantity in BTC amount.
    order = auth_client.place_market_order(product_id='BTC-USD',
                               side='sell',
                               size=orderAmt)
    # Store order id
    orderid = order['id']
    sellPrice = None
    conf = None

    # Check if order id has been filled
    while(True):

        sellPrice, sellFee, conf = orderFillConf(orderid)

        if conf == 1:
            break

    msg = "SELL placed for " + str(orderAmt) + " of BTC @ $" + str(sellPrice)
    logging.info(msg)

    return sellPrice, sellFee




# Function to confirm that the order has been filled
def orderFillConf(orderid):
    fill_hist = []
    count=0
    entry = None
    for fill in auth_client.get_fills(product_id="BTC-USD"):
        fill_hist.append(fill)
        count+=1
        if count > 3:
            break

    for fill in fill_hist:
        if fill['order_id'] == orderid:
            logging.info("Order fill confirmed")
            entry = fill['price']
            fee = fill['fee']
            return entry, fee, 1

    return entry, 0, 0



def setStop(stopPrice, orderAmt):
    # Stop order. `funds` can be used instead of `size` here.
    auth_client.place_stop_order(product_id='BTC-USD',
                              side='sell',
                              price=stopPrice,
                              size=orderAmt)
    msg = "STOP LOSS @ $" + stopPrice
    logging.info(msg)
