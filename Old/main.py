import time
import threading
from typing import Dict, Optional
import pandas as pd

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.common import BarData

def donchian_channel(df: pd.DataFrame, period: int = 30) -> pd.DataFrame:

    df["upper"] = df["high"].rolling(window=period).max()

    df["lower"] = df["low"].rolling(window=period).min()

    df["mid"] = (df["upper"] + df["lower"]) / 2

    return df

class TradingApp(EClient, EWrapper):

    def __init__(self) -> None:

        EClient.__init__(self, self)
        self.data: Dict[int, pd.DataFrame] = {}
        self.nextOrderId: Optional[int] = None

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
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
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[],
        )
        time.sleep(5)
        return self.data[reqId]

    def historicalData(self, reqId: int, bar: BarData) -> None:

        df = self.data[reqId]

        df.loc[
            pd.to_datetime(bar.date),
            ["high", "low", "close"]
        ] = [bar.high, bar.low, bar.close]

        df = df.astype(float)

        self.data[reqId] = df

    @staticmethod
    def get_contract(symbol: str) -> Contract:

        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK" # stock
        contract.exchange = "SMART" # IBKR's smart routing system
        contract.currency = "USD"
        return contract

    def place_order(self, contract: Contract, action: str, order_type: str, quantity: int) -> None:

        order = Order()
        order.action = action # "BUY" or "SELL"
        order.orderType = order_type # "MKT", "LMT", etc
        order.totalQuantity = quantity # share quantity

        self.placeOrder(self.nextOrderId, contract, order) # places order with IBKR's EClient
        self.nextOrderId += 1
        print("Order placed")

def main():
    app = TradingApp()

    # localhost: 127.0.0.1
    # paper trading port = 7497
    # clientID=5 is an arbitrary trading session identifier
    app.connect("127.0.0.1", 7497, clientId=5)

    # opens background thread to run app.run() in parallel
    # daemon=True kills background thread when main thread finishes
    threading.Thread(target=app.run, daemon=True).start()

    while True:
        if isinstance(app.nextOrderId, int):
            print("connected")
            break
        else:
            print("waiting for connection")
            time.sleep(1)

    nvda = TradingApp.get_contract("NVDA")

    data = app.get_historical_data(99, nvda) # nvda reqID=99
    data.tail() # sanity check

    period = 30

    while True:

        print("Getting data for contract...")
        data = app.get_historical_data(99, nvda)

        if len(data) < period:
            print(f"There are only {len(data)} bars of data, skipping...")
            continue

        print("Computing the Donchian Channel...")
        donchian = donchian_channel(data, period=period)

        last_price = data.iloc[-1].close

        upper, lower = donchian[["upper", "lower"]].iloc[-1]

        print(f"Check if last price {last_price} is outside the channels {upper} and {lower}")

        if last_price >= upper:
            print("Breakout detected, going long...")
            app.place_order(nvda, "BUY", "MKT", 10)

        elif last_price <= lower:
            print("Breakout detected, going short...")
            app.place_order(nvda, "SELL", "MKT", 10)

if __name__ == "__main__":
    main()