"""
This module gets 0DTE intraday options data for the SPX.
"""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import BarData
from threading import Event, Timer
import datetime

class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        EWrapper.__init__(self)
        self.data_event = Event()
        self.request_id = 1
        self.strike_prices = []
        self.current_request = 0

    def error(self, reqId, errorCode, errorString):
        print(f"Error: {reqId}, Error Code: {errorCode}, Error String: {errorString}")
        self.data_event.set()

    def historicalData(self, reqId, bar: BarData):
        current_strike, current_right = self.strike_prices[self.current_request][:2]
        print(f"Strike: {current_strike}, Right: {current_right}, Date: {bar.date}, Bid: {bar.low}, Ask: {bar.high}, Volume: {bar.volume}")

    def historicalDataEnd(self, reqId, start, end):
        print(f"End of Historical Data for Request ID: {reqId}\n")
        self.data_event.set()
        self.current_request += 1
        if self.current_request < len(self.strike_prices):
            self.request_next_historical_data()
        else:
            self.disconnect()

    def nextValidId(self, orderId):
        self.request_id = orderId
        self.start()

    def start(self):
        # Get current date
        current_date = datetime.datetime.now().strftime("%Y%m%d")

        # Define contract details
        market_price = 5355
        strike_range = range(market_price - 10, market_price + 10, 5)

        for strike_price in strike_range:
            for right in ["P", "C"]:
                self.strike_prices.append((strike_price, right, current_date))
        
        self.request_next_historical_data()

    def request_next_historical_data(self):
        strike_price, right, current_date = self.strike_prices[self.current_request]

        contract = Contract()
        contract.symbol = "SPX"
        contract.secType = "OPT"
        contract.exchange = "SMART"
        contract.currency = "USD"
        contract.strike = strike_price
        contract.lastTradeDateOrContractMonth = current_date
        contract.right = right

        print(f"Requesting historical data for Strike: {strike_price}, Right: {right}")
        self.reqHistoricalData(self.request_id, contract, "", "1 D", "5 secs", "BID_ASK", 1, 1, False, [])
        self.request_id += 1

    def stop(self):
        self.disconnect()

def main() -> None:
    app = IBApp()
    app.connect("127.0.0.1", 7497, clientId=1)

    Timer(300, app.stop).start()

    app.run()

if __name__ == "__main__":
    main()
