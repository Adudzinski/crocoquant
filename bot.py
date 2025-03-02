import time
import numpy as np
import pandas as pd
from datetime import datetime
import threading
from typing import Dict, Optional
import warnings 
warnings.filterwarnings("ignore")

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.common import BarData
from ib_insync import *


class TradingApp(EClient, EWrapper):

    def __init__(self) -> None:
        EClient.__init__(self, self)
        self.data: Dict[int, pd.Dataframe] = {}

    def error(self, reqId: int, errorCode: int, errorString: str, advanced: dict ={}):# -> None:
        print(f"Error: {reqId}, {errorCode}, {errorString}")

    def nextValidId(self, orderId: int) -> None:
        super().nextValidId(orderId)
        self.nextOrderId = orderId

    def get_historical_data(self, reqId: int, contract: Contract) -> pd.DataFrame:
        self.data[reqId] = pd.DataFrame(columns=["time", "high", "low", "close"])
        self.data[reqId].set_index("time", inplace=True)
        self.reqHistoricalData(
            reqId=reqId,
            contract=contract,
            endDateTime="",
            durationStr="1 D",
            barSizeSetting="1 min",
            whatToShow="MIDPOINT",
            useRTH=0,
            formatDate=2,
            keepUpToDate=False,
            chartOptions=[],
        )
        time.sleep(5)
        return self.data[reqId]

    def historicalData(self, reqId: int, bar: BarData) -> None:
        df = self.data[reqId]
        df.loc[
            pd.to_datetime(bar.date, unit="s"), 
            ["high", "low", "close"]
        ] = [bar.high, bar.low, bar.close]
        df = df.astype(float)
        self.data[reqId] = df

    @staticmethod
    def get_contract(symbol: str) -> Contract:
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        return contract

    def place_order(self, contract: Contract, action: str, order_type: str, quantity: int) -> None:
        order = Order()
        order.action = action
        order.orderType = order_type
        order.totalQuantity = quantity
        self.placeOrder(self.nextOrderId, contract, order)
        self.nextOrderId += 1
        print("Order placed")


app = TradingApp()
app.connect("127.0.0.1",7497, clientId=1)
threading.Thread(target=app.run, daemon=True).start()

nvda=TradingApp.get_contract("NVDA")
nvda
data=app.get_historical_data(99,nvda)
data

#ib=IB()
#ib.connect('127.0.0.1', 7497, 1) #Connection does not work
#stock = Stock('AAPL', 'SMART', 'USD')


#bars = ib.reqHistoricalData(
#    stock,
#    endDateTime='',
#    durationStr='1 D',
#    barSizeSetting='5 mins',
#    whatToShow='MIDPOINT',
#    useRTH=True
#)

#df = util.df(bars)
#print(df)

#ib.disconnect()



#def main():
#    print("Starting CrocoQuant trading bot...")
#    while True:
#        print("Fetching market data...")
#
#        time.sleep(5)  # Simulating a trading loop
#
#if __name__ == "__main__":
#    main()
