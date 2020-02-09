# Data manipulation
import numpy as np
import pandas as pd
import math
# Date time manipulation
import os
from datetime import datetime
import time
import logging
# Gemini python client
import gemini
# Gemini API request
import requests
import json
# Custom package
import telegram as tel

# Telegram chat id
chatid = 000000

# Gemini API credentials
key = '****'
secret = '****'

# Initialize Gemini API client
r = gemini.PrivateClient(key, secret)




def round_down(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n * multiplier) / multiplier

def getCurrPrice():
    price = float(r.get_ticker('BTCUSD')['last'])
    return price

def getBal():
    # Get Balances
    usdbal = 0
    btcbal = 0
    for balance in r.get_balance():
        if balance['currency']=='USD':
            usdbal = float(balance['available'])
        if balance['currency']=='BTC':
            btcbal = float(balance['available'])
    return usdbal, btcbal


def marketBuy(orderAmt, div):

    # Get Balances
    usdbal, btcbal = getBal()
    # Calculate order amounts
    usdorderAmt = round_down((float(usdbal)/div - 0.0036 * (float(usdbal)/div)), 2)
    ask = round_down(float(r.get_ticker("BTCUSD")['ask']) - 0.05, 2)
    btcorderAmt = round_down((usdorderAmt/float(ask)),8)
    origOrderAmt = btcorderAmt
    # Place a limit order at a little below ask price
    ordrplcd = 0

    while(True):
        msg = "Placing new limit buy order @" + str(ask)
        tel.sendMessage(chatid, msg)

        order = r.new_order("BTCUSD", str(btcorderAmt), str(ask), "buy", ["maker-or-cancel"])
        try:
            time.sleep(5)
            orderid = order['order_id']
            ordrplcd = 1
        except:
            ask = round_down(float(r.get_ticker("BTCUSD")['ask']) - 0.05, 2)
            ordrplcd = 0

        if ordrplcd == 1:
            break



    msg = "Initial buy limit order placed @" + str(ask)
    tel.sendMessage(chatid, msg)

#     if order['is_cancelled'] == True and order['reason'] == 'MakerOrCancelWouldTake':
#         return

    # Check whether limit order has been filled
    # Follow market price to place new limit orders
    # After time limit of 6 min, place market order
    start = time.time()
    market = 0
    neword = 0

    while(True):
        if abs(start-time.time()) > 360:
            market = 1
            break

        status = r.status_of_order(orderid)
        if status['is_live'] is False and status['is_cancelled'] == False and status['original_amount'] == status['executed_amount']:
            break
        if status['is_cancelled'] == True and status['original_amount'] != status['executed_amount']:
            neword=1

        if (abs(float(r.get_ticker("BTCUSD")['last']) - float(order['price'])) > 15) or (neword == 1):
            if neword == 0:
                # Cancel latest limit order
                r.cancel_order(orderid)
            # Create new one
            # Check if trade partially filled
            partfill = 0
            for trade in r.get_past_trades("BTCUSD"):
                if trade['order_id']==str(orderid):
                    partfill = round_down(float(trade['amount']),8)
            # Calculate order amounts
            btcorderAmt = btcorderAmt - partfill
            ask = round_down(float(r.get_ticker("BTCUSD")['ask']) - 0.05, 2)

            # Place a limit order at a little below ask price
            ordrplcd = 0

            while(True):
                msg = "Placing new limit buy order @" + str(ask)
                tel.sendMessage(chatid, msg)

                order = r.new_order("BTCUSD", str(btcorderAmt), str(ask), "buy", ["maker-or-cancel"])
                try:
                    time.sleep(5)
                    orderid = order['order_id']
                    ordrplcd = 1
                except:
                    ask = round_down(float(r.get_ticker("BTCUSD")['ask']) - 0.05, 2)
                    ordrplcd = 0

                if ordrplcd == 1:
                    break

            msg = "New limit order placed @" + str(ask)
            tel.sendMessage(chatid, msg)



    if market == 1:
        # Check if trade partially filled
        partfill = 0
        for trade in r.get_past_trades("BTCUSD"):
            if trade['order_id']==str(orderid):
                partfill = round_down(float(trade['amount']),8)
        # Calculate order amounts
        btcorderAmt = btcorderAmt - partfill

        msg = "Market order for " + str(btcorderAmt) + "BTC | Filled amount on limit price " + str(partfill) + "BTC"
        tel.sendMessage(chatid, msg)

        markExec = 0
        while(True):
            currprice = round_down(float(r.get_ticker("BTCUSD")['ask']), 2)

            msg = "Placing new market buy order @" + str(currprice)
            tel.sendMessage(chatid, msg)

            order = r.new_order("BTCUSD", str(btcorderAmt), str(currprice), "buy", ["immediate-or-cancel"])
            try:
                time.sleep(5)
                orderid = order['order_id']
                status = r.status_of_order(orderid)
                if status['is_live'] is False and status['is_cancelled'] == False and status['original_amount'] == status['executed_amount']:
                    markExec = 1
                if status['is_cancelled'] == True and status['original_amount'] != status['executed_amount']:
                    orig = float(status['original_amount']) * float(status['price'])
                    exec = float(status['executed_amount']) * float(status['price'])
                    if abs(orig - exec) <= 5:
                        msg = "Most of market order filled, Fell short by $" + str(abs(orig - exec))
                        tel.sendMessage(chatid, msg)
                        markExec = 1
                    execAmt = round_down(float(status['executed_amount']),8)
                    btcorderAmt = btcorderAmt - execAmt
            except Exception as e:
                markExec = 0
                msg =  e + " Market order failed. Retrying"
                tel.sendMessage(chatid, msg)

            if markExec == 1:
                break



        buyPrice = round(float(r.get_past_trades("BTCUSD")[0]['price']),2)
        buyFee = round(float(r.get_past_trades("BTCUSD")[0]['fee_amount']),2)
        return buyPrice, buyFee

    buyPrice = round(float(r.get_past_trades("BTCUSD")[0]['price']),2)
    buyFee = round(float(r.get_past_trades("BTCUSD")[0]['fee_amount']),2)
    return buyPrice, buyFee




def marketSell(orderAmt, div):

    # Get Balances
    usdbal, btcbal = getBal()
    # Calculate order amounts
    btcorderAmt = round_down(float(btcbal)/div, 8)
    origOrderAmt = btcorderAmt
    bid = round_down(float(r.get_ticker("BTCUSD")['bid']) + 0.03, 2)
    # Place a limit order at a little above bid price
    ordrplcd = 0

    while(True):
        msg = "Placing new limit sell order @" + str(bid)
        tel.sendMessage(chatid, msg)

        order = r.new_order("BTCUSD", str(btcorderAmt), str(bid), "sell", ["maker-or-cancel"])
        try:
            time.sleep(5)
            orderid = order['order_id']
            ordrplcd = 1
        except:
            bid = round_down(float(r.get_ticker("BTCUSD")['bid']) + 0.03, 2)
            ordrplcd = 0

        if ordrplcd == 1:
            break


    msg = "Initial sell limit order placed @" + str(bid)
    tel.sendMessage(chatid, msg)
#     if order['is_cancelled'] == True and order['reason'] == 'MakerOrCancelWouldTake':
#         return

    # Check whether limit order has been filled
    # Follow market price to place new limit orders
    # After time limit of 6 min, place market order
    start = time.time()
    market = 0
    neword = 0

    while(True):
        if abs(start-time.time()) > 360:
            market = 1
            break

        status = r.status_of_order(orderid)
        if status['is_live'] is False and status['is_cancelled'] == False and status['original_amount'] == status['executed_amount']:
            break
        if status['is_cancelled'] == True and status['original_amount'] != status['executed_amount']:
            neword=1

        if (abs(float(r.get_ticker("BTCUSD")['last']) - float(order['price'])) > 15) or (neword==1):
            if neword == 0:
                # Cancel latest limit order
                r.cancel_order(orderid)
            # Create new one
            # Check if trade partially filled
            partfill = 0
            for trade in r.get_past_trades("BTCUSD"):
                if trade['order_id']==str(orderid):
                    partfill = round_down(float(trade['amount']),8)
            # Calculate order amounts
            btcorderAmt = btcorderAmt - partfill
            bid = round_down(float(r.get_ticker("BTCUSD")['bid']) + 0.03, 2)

            # Place a limit order at a little above bid price
            ordrplcd = 0

            while(True):
                msg = "Placing new limit sell order @" + str(bid)
                tel.sendMessage(chatid, msg)

                order = r.new_order("BTCUSD", str(btcorderAmt), str(bid), "sell", ["maker-or-cancel"])
                try:
                    time.sleep(5)
                    orderid = order['order_id']
                    ordrplcd = 1
                except:
                    bid = round_down(float(r.get_ticker("BTCUSD")['bid']) + 0.03, 2)
                    ordrplcd = 0

                if ordrplcd == 1:
                    break


            msg = "New limit order placed @" + str(bid)
            tel.sendMessage(chatid, msg)



    if market == 1:
        # Check if trade partially filled
        partfill = 0
        for trade in r.get_past_trades("BTCUSD"):
            if trade['order_id']==str(orderid):
                partfill = round_down(float(trade['amount']),8)
        # Calculate order amounts
        btcorderAmt = btcorderAmt - partfill

        msg = "Market order for " + str(btcorderAmt) + "BTC | Filled amount on limit price " + str(partfill) + "BTC"
        tel.sendMessage(chatid, msg)

        markExec = 0
        while(True):
            msg = "Placing new market sell order"
            tel.sendMessage(chatid, msg)

            order = r.new_order("BTCUSD", str(btcorderAmt), '0.1', "sell", ["immediate-or-cancel"])
            try:
                time.sleep(5)
                orderid = order['order_id']
                status = r.status_of_order(orderid)
                if status['is_live'] is False and status['is_cancelled'] == False and status['original_amount'] == status['executed_amount']:
                    markExec = 1
                if status['is_cancelled'] == True and status['original_amount'] != status['executed_amount']:
                    orig = float(status['original_amount']) * float(status['price'])
                    exec = float(status['executed_amount']) * float(status['price'])
                    if abs(orig - exec) <= 5:
                        msg = "Most of market order filled, Fell short by $" + str(abs(orig - exec))
                        tel.sendMessage(chatid, msg)
                        markExec = 1
                    execAmt = round_down(float(status['executed_amount']),8)
                    btcorderAmt = btcorderAmt - execAmt
            except Exception as e:
                markExec = 0
                msg =  e + " Market order failed. Retrying"
                tel.sendMessage(chatid, msg)

            if markExec == 1:
                break

        sellPrice = round(float(r.get_past_trades("BTCUSD")[0]['price']),2)
        sellFee = round(float(r.get_past_trades("BTCUSD")[0]['fee_amount']),2)
        return sellPrice, sellFee

    sellPrice = round(float(r.get_past_trades("BTCUSD")[0]['price']),2)
    sellFee = round(float(r.get_past_trades("BTCUSD")[0]['fee_amount']),2)
    return sellPrice, sellFee
