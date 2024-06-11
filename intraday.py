"""
This module fetches data (bid, ask) of traded 0DTE intraday options data for the SPX.
"""
from ib_insync import *
from  datetime import datetime
import time

FILENAME: str = 'intraday.csv'

def get_open_price(ib: IB, date: datetime = datetime.now()) -> float:
    """
    Function that returns the spx's opening price

    Parameters
    ----------
    ib: Interactive brokers object
    date: Date to get the opening price of (today by default)

    Returns
    ----------
    Opening Price of the SPX on date
    """
    spx_contract = Index(symbol='SPX', exchange='CBOE')

    # Request historical data for the SPX contract
    bars = ib.reqHistoricalData(
        spx_contract,
        endDateTime=date,
        durationStr='1 D',
        barSizeSetting='1 day',
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1
    )

    # Print the opening price
    if bars:
        opening_price = bars[0].open
    else:
        raise Exception("Could not fetch opening price")

    return opening_price


def get_data(ib: IB, strike: float, right: str, date: datetime = datetime.now()):
    """
    Generator that yields the bid/ask prices for a 0DTE option.

    Parameters
    ----------
    ib: Interactive brokers object
    strike: Strike price
    right: 'C' or 'P'
    date: Date of option expiry (today by default)

    Returns
    ----------
    List of data [timestamp, strike price, right, bid, ask]
    """
    formatted_date: str = date.strftime("%Y%m%d")      # Using this function inside Option constructor does not work for some reason...
    end_time: str = formatted_date + ' 16:00:01'

    '''data = dict()'''

    contract = Option(
        symbol='SPX', 
        lastTradeDateOrContractMonth=formatted_date, 
        strike=strike, 
        right=right, 
        exchange='SMART', 
        currency='USD'
        )

    bars: list[BarData] = ib.reqHistoricalData(contract, end_time, "1 D", "15 secs", "BID_ASK", 1, 1, False, [])
    ib.sleep(15)

    for bar in bars: 
        '''data["time"] = bar.date
        data["strike"] = strike
        data["right"] = right
        data["bid"] = bar.low
        data["ask"] = bar.high'''

        time = bar.date.strftime('%H%M%S') + '000'
        yield [time, strike, right, bar.low, bar.high]


def file_write(data: dict) -> None:
    """
    Function that writes data to the specified file.

    Parameters
    ----------
    data: List of data [timestamp, strike price, right, bid, ask]
    """
    time, strike, right, bid, ask = data

    with open(FILENAME, 'a') as file:
        file.write(f"{time},{right},'A',{ask},{strike}\n")
        file.write(f"{time},{right},'B',{bid},{strike}\n")
    

def round_to_multiple(x: float, base: int) -> int:
    """
    Helper function that rounds to the nearest multiple of 'base'

    Parameters
    ----------
    x: number to round
    base: multiple to round to

    Returns
    ----------
    x rounded to the nearest multiple of 'base'
    """
    return base * round(x/base)


def create_sublist(list: list, n: int) -> list: 
    """
    Helper function that creates sublists of list by grouping elements in groups of 'len'

    Parameters
    ----------
    list: list to divide into sublists
    n: number of elements in each sublist

    Returns
    ----------
    list of sublists
    """
    return [list[i:i + n] for i in range(0, len(list), n)]

    
def main() -> None:
    CURRENT_TIME: datetime = datetime.now()
    NUM_OF_STRIKES: int = 30

    # Connect to TWS
    ib: IB = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)

    # Get opening price of SPX
    open_price: float = get_open_price(ib)
    print(f"SPX Opening = {open_price}")

    # Round opening to nearest multiple of 5
    open_strike: int = round_to_multiple(open_price, 5)
    print(f"SPX Opening Strike = {open_strike}")
    
    # Get strike prices to capture data from
    strike_range: list[float] = range(open_strike - 5*NUM_OF_STRIKES, open_strike + 5*NUM_OF_STRIKES, 5)  # Strike prices to get data for (30 +/- opening value)
    strike_iterations: list[list] = create_sublist(strike_range, 15)                                                  # Sublists of 15 strikes each, due to rate limit

    for iteration in strike_iterations:
        for strike in iteration:
            for right in ['C','P']:
                for data in get_data(ib, strike, right):
                    file_write(data)

        time.sleep(610) # 10 min cooldown for rate limit

    # Disconnect from IB
    ib.disconnect()


if __name__ == "__main__":
    main()