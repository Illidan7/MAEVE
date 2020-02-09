# Data manipulation
import numpy as np
import pandas as pd
import math

# Date time manipulation
from datetime import datetime
import time
import logging

# Custom packages
import coinbaseproapi as cb
import geminicustomapi as gm
import indicators as ind
import telegram as tel

# Function to store trades recorded during session
def tradeLog(state, entry, exit, orderAmtUSD, orderAmtBTC):
    # Read in tradeLog
    tradeDF = pd.read_csv("tradeLog.csv")
    # Current trade
    trade = {'dateTime': datetime.now(), 'state': state, 'entryPrice': entry, 'exitPrice': exit, 'orderAmtUSD': orderAmtUSD, 'orderAmtBTC':orderAmtBTC, 'netDollar': exit-entry, 'netPerc': ((exit-entry)/entry)*100}
    # Append to tradeLog dataframe
    tradeDF = tradeDF.append(trade, ignore_index=True)
    # Save to CSV
    tradeDF.to_csv("tradeLog.csv", index = False, header = True)

# Function to store events recorded during session
def eventLog(event):
    # Read in tradeLog
    eventDF = pd.read_csv("eventLog.csv")
    # Current trade
    event = {'dateTime': datetime.now(), 'event': event}
    # Append to tradeLog dataframe
    eventDF = eventDF.append(event, ignore_index=True)
    # Save to CSV
    eventDF.to_csv("eventLog.csv", index = False, header = True)



# Dataframe to store trades during session
tradeDF = pd.DataFrame(columns=['dateTime', 'state', 'entryPrice', 'exitPrice', 'orderAmtUSD', 'orderAmtBTC', 'netDollar', 'netPerc'])
tradeDF.to_csv("tradeLog.csv", index = False, header = True)

# Dataframe to store events during session
eventDF = pd.DataFrame(columns=['dateTime', 'event'])
eventDF.to_csv("eventLog.csv", index = False, header = True)

# Telegram chat id
chatid = 0000000

# Log file set up
logging.basicConfig(filename="botLog.log", level=logging.INFO)

# State transition
#stateHist = []

# Initial stop and target ranges
stopGap = 0.015
tgtGap = 0.01

# Track positions in the market
position = {1:0, 2:0, 3:0}
shortSet = {1:0, 2:0, 3:0}
# Order amounts
orderAmtsUSD = {1:0, 2:0, 3:0}
orderAmtsBTC = {1:0, 2:0, 3:0}
# Entry prices
entryPrice = {1:0, 2:0, 3:0}
# Stop prices
stopPrice = {1:0, 2:0, 3:0}
# Target prices
tgtPrice = {1:0, 2:0, 3:0}
# Exit prices
exitPrice = {1:0, 2:0, 3:0}
# Tracks number of targets hit; Helps to trail stop losses and set new targets
tgtHit = {1:0, 2:0, 3:0}
# Tracks crossover occurrences and prevents overtrading
lockState = {1:0, 2:0, 3:0}
unlockState = {1:300, 2:300, 3:300}
# Heartbeat
hrtbt = 0

msg = "MAEVE started @" + str(datetime.now())
tel.sendMessage(chatid, msg)

while(True):

    logging.info("############################################")
    logging.info("Strategy Run @" + str(datetime.now()))
    logging.info("#############################################")

    # Monitor heartbeat
    hrtbt+=1
    if hrtbt == 120:
        msg = "MAEVE hard at work @" + str(datetime.now())
        tel.sendMessage(chatid, msg)
        hrtbt = 0

    # Get current price
    price = gm.getCurrPrice()
    # Get current balances
    USD_bal, BTC_bal = gm.getBal()

    # Get historical price data for BTC (hour - 3600, 15min - 900)
    hourlyBTC = cb.getPriceData('BTC', 3600)
    currow = pd.DataFrame({'unixtime': 0, 'low':0, 'high': 0, 'open': 0, 'close':price, 'volume': 0, 'localtime': datetime.now()}, index =[0])
    hourlyBTC = pd.concat([currow, hourlyBTC[:]]).reset_index(drop = True)

    # Get moving averages for hourly
    MA8 = ind.movAvg(hourlyBTC, 8)
    MA13 = ind.movAvg(hourlyBTC, 13)
    MA22 = ind.movAvg(hourlyBTC, 22)
    MA55 = ind.movAvg(hourlyBTC, 55)
    MA100 = ind.movAvg(hourlyBTC, 100)

    logging.info(MA8)
    logging.info(MA13)
    logging.info(MA22)
    logging.info(MA55)

    #####################
    # Unlock countdown
    #####################

    for i in range(0,3):
        state = i + 1
        if unlockState[state] < 300 and lockState[state]==1:
            unlockState[state] = unlockState[state] - 1
            if unlockState[state] <= 0:
                lockState[state] = 0
                unlockState[state] = 300
                msg = "State " + str(state) + " unlocked: Time unlock"
                logging.info(msg)
                # Event log
                eventLog(msg)
                # Telegram log
                msg = "State " + str(state) + " unlocked: Time unlock"
                tel.sendMessage(chatid, msg)



    #################
    # LONG signals
    #################

    # Long signal 1
    if MA8 > MA13:
        state = 1
        if position[state] == 0 and lockState[state] == 0:
            # Update state history
            #stateHist.append(1)
            div = 0
            # Determine order amount
            if (position[state]+position[state+1]+position[state+2]) == 0:
                orderAmtUSD = math.floor(USD_bal/3 * 100)/100.0
                div=3
            elif (position[state]+position[state+1]+position[state+2]) == 1:
                orderAmtUSD = math.floor(USD_bal/2 * 100)/100.0
                div=2
            else:
                orderAmtUSD = math.floor(USD_bal * 100)/100.0
                div=1

            # Place BUY order
            entryPrice[state], fee = gm.marketBuy(orderAmtUSD, div)
            entryPrice[state] = round(float(entryPrice[state]),2)
            fee = round(float(fee),2)+0.01
            orderAmtBTC = round(float((orderAmtUSD - fee)/entryPrice[state]),8)

            orderAmtsUSD[state] = orderAmtUSD
            orderAmtsBTC[state] = orderAmtBTC

            # Update balances
            USD_bal = USD_bal - orderAmtUSD
            BTC_bal = BTC_bal + orderAmtBTC

            # Update position
            position[state]=1

            # Event log
            eventLog("Postion 1 entry")

            # Determine stop price and place stop order
            stopPrice[state] = entryPrice[state] - (stopGap * entryPrice[state])

            # Determine target price
            tgtPrice[state] = entryPrice[state] + (tgtGap * entryPrice[state])

            # Telegram log
            msg = "Postion 1 entry @" + str(entryPrice[state]) + " Stop: " + str(stopPrice[state]) + " Target:" + str(tgtPrice[state])
            tel.sendMessage(chatid, msg)


    # Long signal 2
    if MA13 > MA22 and MA8 > MA13:
        state = 2
        if position[state] == 0 and lockState[state] == 0:
            # Update state history
            #stateHist.append(2)
            div = 0
            # Determine order amount
            if (position[state-1]+position[state]+position[state+1]) == 0:
                orderAmtUSD = math.floor(USD_bal/3 * 100)/100.0
                div = 3
            elif (position[state-1]+position[state]+position[state+1]) == 1:
                orderAmtUSD = math.floor(USD_bal/2 * 100)/100.0
                div = 2
            else:
                orderAmtUSD = math.floor(USD_bal * 100)/100.0
                div = 1

            # Place BUY order
            entryPrice[state], fee = gm.marketBuy(orderAmtUSD, div)
            entryPrice[state] = round(float(entryPrice[state]),2)
            fee = round(float(fee),2)+0.01
            orderAmtBTC = round(float((orderAmtUSD - fee)/entryPrice[state]),8)

            orderAmtsUSD[state] = orderAmtUSD
            orderAmtsBTC[state] = orderAmtBTC

            # Update balances
            USD_bal = USD_bal - orderAmtUSD
            BTC_bal = BTC_bal + orderAmtBTC

            # Update position
            position[state]=1

            # Event log
            eventLog("Postion 2 entry")

            # Determine stop price and place stop order
            stopPrice[state] = entryPrice[state] - (stopGap * entryPrice[state])

            # Determine target price
            tgtPrice[state] = entryPrice[state] + (tgtGap * entryPrice[state])

            # Telegram log
            msg = "Postion 2 entry @" + str(entryPrice[state]) + " Stop: " + str(stopPrice[state]) + " Target:" + str(tgtPrice[state])
            tel.sendMessage(chatid, msg)

    # Long signal 3
    if MA22 > MA55 and MA13 > MA22 and MA8 > MA13:
        state = 3
        if position[state] == 0 and lockState[state] == 0:

            # Update state history
            #stateHist.append(3)
            div = 0
            # Determine order amount
            if (position[state-2]+position[state-1]+position[state]) == 0:
                orderAmtUSD = math.floor(USD_bal/3 * 100)/100.0
                div = 3
            elif (position[state-2]+position[state-1]+position[state]) == 1:
                orderAmtUSD = math.floor(USD_bal/2 * 100)/100.0
                div = 2
            else:
                orderAmtUSD = math.floor(USD_bal * 100)/100.0
                div = 1

            # Place BUY order
            entryPrice[state], fee = gm.marketBuy(orderAmtUSD, div)
            entryPrice[state] = round(float(entryPrice[state]),2)
            fee = round(float(fee),2)+0.01
            orderAmtBTC = round(float((orderAmtUSD - fee)/entryPrice[state]),8)

            orderAmtsUSD[state] = orderAmtUSD
            orderAmtsBTC[state] = orderAmtBTC

            # Update balances
            USD_bal = USD_bal - orderAmtUSD
            BTC_bal = BTC_bal + orderAmtBTC

            # Update position
            position[state]=1

            # Event log
            eventLog("Postion 3 entry")

            # Determine stop price and place stop order
            stopPrice[state] = entryPrice[state] - (stopGap * entryPrice[state])

            # Determine target price
            tgtPrice[state] = entryPrice[state] + (tgtGap * entryPrice[state])

            # Telegram log
            msg = "Postion 3 entry @" + str(entryPrice[state]) + " Stop: " + str(stopPrice[state]) + " Target:" + str(tgtPrice[state])
            tel.sendMessage(chatid, msg)



    ###################
    # SHORT signals
    ###################

    # Short signal 1
    if MA13 > MA8:

        # Release lock on trading
        if lockState[1] == 1:
            lockState[1] = 0
            unlockState[1] = 300
            logging.info("State 1 unlocked")
            # Event log
            eventLog("State 1 unlocked: State change unlock")
            # Telegram log
            msg = "State 1 unlocked: State change unlock"
            tel.sendMessage(chatid, msg)

        # If state 1 has an existing position
        # Compare the price and stop price
        # If 0.5% within each other then sell position
        # If not update stopPrice to within 0.75% of current price

        if (position[1] == 1) and (shortSet[1]==0):
            percdiff = ((price - stopPrice[1])/price) *100
            if percdiff > 0.5:
                stopPrice[1] = price - (0.005 * price)
                shortSet[1] = 1
                # Event log
                eventLog("Position 1 shortSet 1")
                # Telegram log
                msg = "State 1 short signal. Stop price @ $" + str(stopPrice[1])
                tel.sendMessage(chatid, msg)
            #     exitPrice[1] = float(cb.marketSell(orderAmtsBTC[1]))
            #     position[1]=0
            #     # Log completed trade
            #     tradeLog(1, entryPrice[1], exitPrice[1], orderAmtsUSD[1], orderAmtsBTC[1])
            #
            # else:


        if (position[2]==1) and (shortSet[2]==0):
            percdiff = ((price - stopPrice[2])/price) *100
            if percdiff > 0.75:
                stopPrice[2] = price - (0.0075 * price)
                shortSet[2] = 0.5
                # Event log
                eventLog("Position 2 shortSet 0.5")

    # Short signal 2
    if MA22 > MA13 and MA13 > MA8:

        # Release lock on trading
        if lockState[2] == 1:
            lockState[2] = 0
            unlockState[2] = 300
            logging.info("State 2 unlocked")
            # Event log
            eventLog("State 2 unlocked: State change unlock")
            # Telegram log
            msg = "State 2 unlocked: State change unlock"
            tel.sendMessage(chatid, msg)

        # If state 1 has an existing position
        # Compare the price and stop price
        # If 0.5% within each other then sell position
        # If not update stopPrice to within 0.75% of current price

        if (position[2] == 1) and (shortSet[2]<1):
            percdiff = ((price - stopPrice[2])/price) *100
            if percdiff > 0.5:
                stopPrice[2] = price - (0.005 * price)
                shortSet[2] = 1
                # Event log
                eventLog("Position 2 shortSet 1")
                # Telegram log
                msg = "State 2 short signal. Stop price @ $" + str(stopPrice[2])
                tel.sendMessage(chatid, msg)
            #     exitPrice[2] = float(cb.marketSell(orderAmtsBTC[2]))
            #     position[2]=0
            #     # Log completed trade
            #     tradeLog(2, entryPrice[2], exitPrice[2], orderAmtsUSD[2], orderAmtsBTC[2])
            # else:


        if (position[3]==1) and (shortSet[3]==0):
            percdiff = ((price - stopPrice[3])/price) *100
            if percdiff > 0.5:
                stopPrice[3] = price - (0.005 * price)
                shortSet[3] = 0.5
                # Event log
                eventLog("Position 3 shortSet 0.5")
                # Telegram log
                msg = "State 3 early short signal. Stop price @ $" + str(stopPrice[2])
                tel.sendMessage(chatid, msg)

    # Short signal 3
    if MA55 > MA22 and MA22 > MA13 and MA13 > MA8:

        # Release lock on trading
        if lockState[3] == 1:
            lockState[3] = 0
            unlockState[3] = 300
            logging.info("State 3 unlocked")
            # Event log
            eventLog("State 3 unlocked: State change unlock")
            # Telegram log
            msg = "State 3 unlocked: State change unlock"
            tel.sendMessage(chatid, msg)

        # If state 1 has an existing position
        # Compare the price and stop price
        # If 0.5% within each other then sell position
        # If not update stopPrice to within 0.75% of current price

        # if (position[1]==1) and (shortSet[1]<=1):
        #     percdiff = ((price - stopPrice[1])/price) *100
        #     if percdiff > 0.25:
        #         stopPrice[1] = price - (0.0025 * price)
        #         shortSet[1] = 1.5
        #         # Event log
        #         eventLog("Position 1 shortSet 1.5")

            # exitPrice[1], fee = cb.marketSell(orderAmtsBTC[1])
            # exitPrice[1] = float(exitPrice[1])
            # fee = float(fee)
            # position[1]=0
            # # Log completed trade
            # tradeLog(1, entryPrice[1], exitPrice[1], orderAmtsUSD[1], orderAmtsBTC[1])

        # if (position[2] == 1) and (shortSet[2]<=1):
        #     percdiff = ((price - stopPrice[2])/price) *100
        #     if percdiff > 0.25:
        #         stopPrice[2] = price - (0.0025 * price)
        #         shortSet[2] = 1.5
        #         # Event log
        #         eventLog("Position 2 shortSet 1.5")

            # exitPrice[2], fee = cb.marketSell(orderAmtsBTC[2])
            # exitPrice[2] = float(exitPrice[2])
            # fee = float(fee)
            # position[2]=0
            # # Log completed trade
            # tradeLog(2, entryPrice[2], exitPrice[2], orderAmtsUSD[2], orderAmtsBTC[2])

        if (position[3]==1) and (shortSet[3]<1):
            percdiff = ((price - stopPrice[3])/price) *100
            if percdiff > 0.5:
                stopPrice[3] = price - (0.005 * price)
                shortSet[3] = 1
                # Event log
                eventLog("Position 3 shortSet 1")
                # Telegram log
                msg = "State 3 short signal. Stop price @ $" + str(stopPrice[3])
                tel.sendMessage(chatid, msg)

    ###########################
    # Position management
    ###########################
    for state, value in position.items():
        # If position open
        if value == 1:
            # Compare current price with stop price
            if price < stopPrice[state]:
                logging.info("Position: " + str(state) + " Status: Stop loss hit")
                # Find div
                if (position[1]+position[2]+position[3]) == 3:
                    div = 3
                elif (position[1]+position[2]+position[3]) == 2:
                    div = 2
                else:
                    div = 1
                # Exit position
                exitPrice[state], fee = gm.marketSell(orderAmtsBTC[state], div)
                exitPrice[state] = float(exitPrice[state])
                fee = round(float(fee),2)+0.01

                position[state] = 0
                tgtHit[state] = 0
                shortSet[state] = 0
                # Event log
                msg = "Position " + str(state) + " exit"
                eventLog(msg)
                # Telegram log
                msg = "Position " + str(state) + " exit @" + str(exitPrice[state])
                tel.sendMessage(chatid, msg)
                # Log completed trade
                tradeLog(state, entryPrice[state], exitPrice[state], orderAmtsUSD[state], orderAmtsBTC[state])

                # Prevent overtrading after stop is hit
                if state==1 and MA8 > MA13:
                    lockState[state] = 1
                    unlockState[state] = unlockState[state] - 1
                    logging.info("State 1 locked")
                    # Event log
                    eventLog("State 1 locked")
                    # Telegram log
                    msg = "State 1 locked"
                    tel.sendMessage(chatid, msg)
                if state==2 and MA8 > MA13 and MA13 > MA22:
                    lockState[state] = 1
                    unlockState[state] = unlockState[state] - 1
                    logging.info("State 2 locked")
                    # Event log
                    eventLog("State 2 locked")
                    # Telegram log
                    msg = "State 2 locked"
                    tel.sendMessage(chatid, msg)
                if state==3 and MA8 > MA13 and MA13 > MA22 and MA22 > MA55:
                    lockState[state] = 1
                    unlockState[state] = unlockState[state] - 1
                    logging.info("State 3 locked")
                    # Event log
                    eventLog("State 3 locked")
                    # Telegram log
                    msg = "State 3 locked"
                    tel.sendMessage(chatid, msg)


            # Compare current price with target price
            if price > tgtPrice[state]:
                # Update Target hit counter
                tgtHit[state] += 1
                logging.info("Position: " + str(state) + " Status: Target hit count: " + str(tgtHit[state]))
                # Event log
                msg = "Position " + str(state) + " Target " + str(tgtHit[state]) + " Hit"
                eventLog(msg)
                # Telegram log
                msg = "Position " + str(state) + " Target " + str(tgtHit[state]) + " Hit @" + str(tgtPrice[state])
                tel.sendMessage(chatid, msg)

                # Update Target and Stop
                if tgtHit[state] == 1:
                    tgtPrice[state] = entryPrice[state] * (1.015)
                    stopPrice[state] = entryPrice[state] * (1.0025)
                else:
                    tgtPrice[state] = entryPrice[state] * (1.015 + (0.005 * tgtHit[state]))
                    stopPrice[state] = entryPrice[state] * (1.0025 + (0.005 * tgtHit[state]))

                # if tgtHit[state] < 3:
                #     tgtPrice[state] = entryPrice[state] * (1+(0.01+(0.005*float(tgtHit[state]))))
                #     if state == 1:
                #         stopPrice[state] = entryPrice[state] * (1+(0.005*float(tgtHit[state])))
                #     else:
                #         stopPrice[state] = stopPrice[state] + ((0.007*float(tgtHit[state]))* entryPrice[state])
                # else:
                #     tgtPrice[state] = entryPrice[state] * (1+(0.012*float(tgtHit[state])))
                #     stopPrice[state] = entryPrice[state] * (0.97+(0.014*float(tgtHit[state])))

                # Telegram log
                msg = "Position " + str(state) + " | New target @" + str(tgtPrice[state]) + " New Stop @" + str(stopPrice[state])
                tel.sendMessage(chatid, msg)

            if position[state]==1:
                logging.info("Position: " + str(state) + " Status: HOLD")
                logging.info("Entry @$" + str(entryPrice[state]))
                logging.info("Stop @$" + str(stopPrice[state]) + " Target @$" + str(tgtPrice[state]))
        else:
            logging.info("Position: " + str(state) + " Status: Not Entered")


    #Time delay for Strategy run
    time.sleep(30)
