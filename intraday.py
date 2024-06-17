"""
This module fetches data (bid, ask) of traded 0DTE intraday options data for the SPX.
"""
from ib_insync import *
from datetime import datetime, timedelta
import struct
import time

FILENAME: str = 'intraday.bin'

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


def get_data(ib: IB, strike: float, right: str, interval_end_time: datetime = None, date: datetime = datetime.now()):
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

    if interval_end_time is None:   
        end_time: str = formatted_date + ' 16:00:00'
    else:
        end_time: str = formatted_date + interval_end_time.strftime(' %H:%M:%S')

    contract = Option(
        symbol='SPX', 
        lastTradeDateOrContractMonth=formatted_date, 
        strike=strike, 
        right=right, 
        exchange='SMART', 
        currency='USD'
        )

    bars: list[BarData] = ib.reqHistoricalData(contract, end_time, "3600 S", "5 secs", "BID_ASK", 1, 1, False, [])  # Historical data per hour, 5 second step size
    ib.sleep(15)

    for bar in bars: 
        time = int(bar.date.strftime('%H%M%S') + '000')

        yield [time, int(strike), right, bar.low, bar.high]


def file_write(data: list, filename: str, bin: bool = False) -> None:
    """
    Function that writes data to the specified file with columns:  Timestamp, CallPut, Side, BidAsk, Strike
    If file is in binary format, 0/1 = Call/Put and 0/1 = Bid/Ask

    Parameters
    ----------
    data: List of data [timestamp, strike price, right, bid, ask]
    filename: name of file to write to
    bin: True if binary file/data
    """
    # Unpack data
    time, strike, right, bid, ask = data    

    if bin:
        #Dictionaires for converting call/put and bid/ask to 0 and 1
        cp = {"C": 0, "P": 1}
        ba = {"B": 0, "A": 1}

        with open(filename, 'ab') as file:
            file.write(struct.pack('iiifi', time, cp[right], ba['B'], bid, strike))
            file.write(struct.pack('iiifi', time, cp[right], ba['A'], ask, strike))

    elif not bin:
        with open(filename, 'a') as file:
            file.write(f"{time},{right},'B',{bid},{strike}\n")
            file.write(f"{time},{right},'A',{ask},{strike}\n")

    else:
        raise SyntaxError("bin must be True or False")


def get_time_intervals(interval_length: int, time_unit: str) -> list[datetime]:
    """
    Function that creates a list of time intervals specified by 'delta' from 9:30 AM to 4:00 PM

    Parameters
    ----------
    interval_length: Time Interval
    time_unit: hours, minutes, or seconds
    
    Returns
    ----------
    list of time intervals as datetime objects
    **Note: does not include 9:30**
    """
    if time_unit == "hours":
        delta = timedelta(hours=interval_length)
    elif time_unit == "minutes":
        delta = timedelta(minutes=interval_length)
    elif time_unit == "seconds":
        delta = timedelta(seconds=interval_length)
    else:
        raise SyntaxError("time_unit must be 'hours', 'minutes', or 'seconds'")

    now: datetime = datetime.now()
    current: datetime = datetime(now.year, now.month, now.day, 9, 30, 0)          # Initalize as 9:30 AM
    end: datetime = datetime(now.year, now.month, now.day, 16, 0, 0)

    intervals: list[datetime] = []

    while current < end - delta:
        current += delta
        intervals.append(current)

    if end not in intervals:
        intervals.append(end)

    return intervals


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
    NUM_OF_STRIKES: int = 30

    tik = time.time()
    start = datetime.now()
    print(f"start time = {start}")

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
    strike_iterations: list[list] = create_sublist(strike_range, 15)                                      # Sublists of 15 strikes each, due to rate limit

    intervals = get_time_intervals(1, "hours")

    for end_interval in intervals:                                              # Get data for every 1 hour in the trading day
        for iteration in strike_iterations:                                     # 4 Groups of 15 Strikes
            for strike in iteration:                                            # Each of the 15 Strikes
                for right in ['C','P']:                                         # Call/Put
                    for data in get_data(ib, strike, right, end_interval):      # Data at 15 second intervals
                        file_write(data, FILENAME, True)

            time.sleep(240)                                                     # 10 min cooldown for rate limit every 15 strikes

    # Disconnect from IB
    ib.disconnect()

    end = datetime.now()
    print(f"end time = {end}")

    tok = time.time()
    print(f"Runtime: {tok-tik} seconds")

if __name__ == "__main__":
    main()