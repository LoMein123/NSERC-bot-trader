"""
This module contains a function (get_data) that fetches data (bid, ask) of traded 0DTE intraday options data for the SPX and creates a file.
"""
from ib_insync import *
from datetime import datetime, timedelta
import struct
import time

EOFSTR = "&&&--EOF--&&&"

def get_open_price(ib: IB, date: datetime) -> float:
    """
    Function that returns the spx's opening price

    Parameters
    ----------
    ib: Interactive brokers object
    date: Date to get the opening price of

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


def fetch_data(ib: IB, strike: float, right: str, side: str, date: datetime, interval_end_time: datetime = None):
    """
    Generator that yields the bid/ask prices for a 0DTE option.

    Parameters
    ----------
    ib: Interactive brokers object
    strike: Strike price
    right: 'C' or 'P'
    side: 'B' or 'A'
    date: Date of option expiry

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
        currency='USD',
        multiplier=100
        )

    if side not in ['B','A']:
        raise SyntaxError("Side must be 'B' or 'A'.")

    # Historical data every 30 mins, 1 second resolution
    # Intervals and Resolution settings -- https://interactivebrokers.github.io/tws-api/historical_limitations.html
    bars: list[BarData] = ib.reqHistoricalData(contract, end_time, "1800 S", "1 secs", f"{'BID' if side == 'B' else 'ASK'}", 1, 1, False, [])
    ib.sleep(15)

    for bar in bars: 
        time = int(bar.date.strftime('%H%M%S') + '000')

        print(side)

        yield [time, int(strike), right, side, bar.low, bar.high]


def file_write(data: list, filename: str, binary: bool = False) -> None:
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
    time, strike, right, side, bid, ask = data    

    if binary:
        #Dictionaires for converting call/put and bid/ask to 0 and 1
        cp = {"C": 0, "P": 1}
        ba = {"B": 0, "A": 1}

        with open(filename, 'ab') as file:
            file.write(struct.pack('iiifi', time, cp[right], ba[side], bid, strike))

        '''for testing'''
        with open('intraday.csv', 'a') as file:
            file.write(f"{time},{right},{side},{ask},{strike}\n")


    elif not binary:
        with open(filename, 'a') as file:
            file.write(f"{time},{right},{side},{ask},{strike}\n")

    else:
        raise SyntaxError("binary must be True or False")
    

def file_end(filename: str, bin: bool = False) -> None:
    """
    Function that writes a special end of file character(s) to the given file.
    End of file = '&&&--EOF--&&&'

    Parameters
    ----------
    filename: name of file to write to
    bin: True if binary file/data
    """
    if bin:
        #with open(filename, 'ab') as file:
            #file.write(struct.pack('iiifi', time, cp[right], ba['B'], bid, strike))

        ##### FOR TESTING
        with open('intraday.csv', 'a') as file:
            file.write(EOFSTR)


    elif not bin:
        with open(filename, 'a') as file:
            file.write(EOFSTR)

    else:
        raise SyntaxError("bin must be True or False")
    

def file_merge(filenames: list[str], out_filename: str) -> None:
    """
    Function that merges files together if they have the end of file character(s)
    
    Parameters
    ----------
    filenames: list of files to merge by name
    out_filename: name of merged file 
    """
    with open(out_filename, 'w') as outfile:
        for file in filenames:
            with open(file) as infile:
                for line in infile:
                    if line != EOFSTR:
                        outfile.write(line)


def get_time_intervals(date: datetime, interval_length: int, time_unit: str) -> list[datetime]:
    """
    Function that creates a list of time intervals specified by 'delta' from 9:30 AM to 4:00 PM.

    Parameters
    ----------
    date: date to split into intervals
    interval_length: Time Interval
    time_unit: hours, minutes, or seconds
    
    Returns
    ----------
    list of time intervals as datetime objects
    **Note: does not include 9:30**
    """
    intervals: list[datetime] = []

    start: datetime = datetime(date.year, date.month, date.day, 9, 30, 0)   # 9:30 AM
    end: datetime = datetime(date.year, date.month, date.day, 16, 0, 0)     # 4:00 PM

    if time_unit == "hours":
        delta = timedelta(hours=interval_length)
    elif time_unit == "minutes":
        delta = timedelta(minutes=interval_length)
    elif time_unit == "seconds":
        delta = timedelta(seconds=interval_length)
    else:
        raise SyntaxError("time_unit must be 'hours', 'minutes', or 'seconds'")

    # Every interval_length
    current: datetime = start
    while current < end - delta:
        current += delta
        intervals.append(current)

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


def parse_filename(filename: str) -> tuple[str, bool]:
    """
    Function that parses the filename and extension

    Parameters
    ----------
    filename: filename

    Returns
    ----------
    Filename without extension
    Boolean of if file is binary
    """
    f = filename.split('.')

    if len(f) > 3:
        raise SyntaxError("Invalid filetype")

    filename_no_extension = f[0]
    binary = True if f[-1].lower() == 'bin' else False

    return filename_no_extension, binary


def get_data(filename: str, file_number: int = 0, date: datetime = datetime.now(), binary: bool = False) -> None:
    """
    Function that gets all all options data for the SPX at 1 second intervals on a given date, then writes to a file.
    Splits the data into several files, then combines them at the end so that if a crash occurs, can continue from a specified file.

    Parameters
    ----------
    filename: filename
    file_number: Used for data recovery after crash; the file number to start from - default 0
    date: date of strikes - default today
    binary: True if binary file - default False
    """
    NUM_OF_STRIKES: int = 30

    # Connect to TWS
    ib: IB = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)

    # Get opening price of SPX
    date = date.replace(hour=9, minute=40)
    open_price: float = get_open_price(ib, date)
    print(f"SPX Opening = {open_price}")

    # Round opening to nearest multiple of 5
    open_strike: int = round_to_multiple(open_price, 5)
    print(f"SPX Opening Strike = {open_strike}")
    
    # Get strike prices to capture data from (NUM_OF_STRIKES +/- opening value)
    strike_range: range = range(open_strike - 5*NUM_OF_STRIKES, open_strike + 5*NUM_OF_STRIKES, 5)
    print(f"Strike Range: {strike_range[0]}-{strike_range[-1]}")
    
    # Sublists of 15 strikes each, due to rate limit
    strike_groups: list[list] = create_sublist(strike_range, 15)

    # Time intervals of 30 mins, due to rate limit
    intervals: list[datetime] = get_time_intervals(date, 30, "minutes")

    # Check if file number can exist
    num_intervals = len(intervals)
    if num_intervals <= file_number:
        raise SyntaxError(f"File number must be less than {num_intervals}")

    # Get data for every time interval, starting from the file_number-th interval
    filenames: list[str] = []
    for i in range(file_number, num_intervals):
        current_interval: datetime = intervals[i]

        current_filename: str = f"{filename}{i}{'.bin' if binary else '.csv'}"
        filenames.append(current_filename)
        open(current_filename, 'w').close()

        for strike_group in strike_groups:                                                        # 4 Groups of 15 Strikes
            for strike in strike_group:                                                           # Each of the 15 Strikes
                for right in ['C', 'P']:                                                          # Call/Put
                    for side in ['B', 'A']:                                                       # Bid/Ask
                        for data in fetch_data(ib, strike, right, side, date, current_interval):  # Get data at 1 second intervals
                            file_write(data, current_filename)

            time.sleep(370)                                                                       # 6 min cooldown every 15 strikes
        file_end(current_filename)

    # Merge all files together
    file_merge(filenames, out_filename=filename)

    # Disconnect from IB
    ib.disconnect()


## For Testing
def main() -> None:
    FILENAME = 'intraday'
    fileNumber = 7
    date = datetime(2024, 7, 3)
    isBinary = False

    tik = time.time()
    start = datetime.now()
    print(f"start time = {start}")

    get_data(FILENAME, fileNumber, date, isBinary)

    end = datetime.now()
    print(f"end time = {end}")

    tok = time.time()
    print(f"Runtime: {tok-tik} seconds")


if __name__ == "__main__":
    main()