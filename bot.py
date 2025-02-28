import time
import numpy as np
import pandas as pd
from ib_insync import *

ib=IB()
ib.connect('127.0.0.1', 7497, 1) #Connection does not work
stock = Stock('AAPL', 'SMART', 'USD')


bars = ib.reqHistoricalData(
    stock,
    endDateTime='',
    durationStr='1 D',
    barSizeSetting='5 mins',
    whatToShow='MIDPOINT',
    useRTH=True
)

df = util.df(bars)
print(df)

ib.disconnect()



#def main():
#    print("Starting CrocoQuant trading bot...")
#    while True:
#        print("Fetching market data...")
#
#        time.sleep(5)  # Simulating a trading loop
#
#if __name__ == "__main__":
#    main()
