"""
This module contains a function (get_data) that fetches data (bid, ask) of traded 0DTE intraday options data for the SPX and creates a file.
"""
from ib_insync import *
from datetime import datetime
import time
import pandas as pd
import numpy as np
import os.path
import glob
import pyarrow as pa
import pyarrow.parquet as pq

class log():
    """
    Log file custom class
    """
    def __init__(self, log_filename: str):
        """
        Constructor that creates the log file of specified name or clears any previous log file of the same name

        Parameters
        ----------
        log_filename: filename of log file
        """
        self.log_filename = log_filename
        open(self.log_filename, 'w').close()

    def write(self, string: str) -> None:
        """
        Method that logs a string to the log file.

        Parameters
        ----------
        string: string to log
        """
        print(string)

        with open(self.log_filename, 'a') as log_file:
            log_file.write(string + "\n")


def get_open_price(ib: IB, date: datetime) -> float:
    """
    Returns the SPX's opening price on a given date.

    Parameters
    ----------
    ib: Interactive brokers object
    date: Date to get the opening price of
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
        raise Exception("Could not fetch opening price.")

    return opening_price


def fetch_data(ib: IB, strike: float, price_type: str, interval_end_time: datetime) -> pd.DataFrame:
    """
    Returns a pandas dataframe containing either the "CallBid", "CallAsk", "PutBid", or "PutAsk" 
    price of the SPX for a given strike at every second of a 30 min interval.

    Parameters
    ----------
    ib: Interactive brokers object
    strike: Strike price
    price_type: "CallBid", "CallAsk", "PutBid", or "PutAsk"
    interval_end_time: Ending time of the 30 min interval to get data of (e.g For data between 9:30 and 10:00, enter 10:00 as argument)
    """
    typeDict = {
        "CallBid": ("C", "BID"), 
        "CallAsk": ("C", "ASK"), 
        "PutBid": ("P", "BID"), 
        "PutAsk": ("P", "ASK"), 
    }

    try:
        right = typeDict[price_type][0]
        side = typeDict[price_type][1]
    except KeyError:
        raise SyntaxError('price_type must be either: "CallBid", "CallAsk", "PutBid", "PutAsk"')

    formatted_date: str = interval_end_time.strftime("%Y%m%d")      # Using this function inside Option constructor does not work for some reason...
    end_time: str = formatted_date + interval_end_time.strftime(' %H:%M:%S') + " America/New_York"

    contract = Option(
        symbol='SPX', 
        lastTradeDateOrContractMonth=formatted_date, 
        strike=strike, 
        right=right, 
        exchange='SMART', 
        currency='USD',
        multiplier=100
        )

    # Historical data every 30 mins, 1 second resolution
    # Intervals and Resolution settings -- https://interactivebrokers.github.io/tws-api/historical_limitations.html
    bars: list[BarData] = ib.reqHistoricalData(contract, end_time, "1800 S", "1 secs", side, 1, 1, False, [])
    ib.sleep()

    # Fix dataframe formatting
    try:
        df = util.df(bars)
        df = df[['date','close']]
        df = df.rename(columns={'close': price_type})
        df.set_index('date', inplace=True)
        df.index = pd.to_datetime(df.index)
    except TypeError:
        # Error happens here if no data
        pass

    return df


def file_write(df: pd.DataFrame, filepath: str) -> None:
    """
    Function that writes data to the specified parquet file with columns ["CallBid", "CallAsk", "PutBid", "PutAsk"]

    Parameters
    ----------
    df: dataframe of data
    filepath: path of file to write to
    """
    # Append if file exists
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        existing_df = pd.read_parquet(filepath)
        combined_df = pd.concat([existing_df, df], ignore_index=True)
        table = pa.Table.from_pandas(combined_df)
        pq.write_table(table, filepath)
        
    # Create file it it doesn't exist
    else:
        pq.write_table(pa.Table.from_pandas(df), filepath)

    '''# Convert DataFrame to numpy array
    data_array: np.ndarray = df.to_numpy()

    # Append to binary file
    with open(filepath, 'ab') as file:
        data_array.tofile(file)'''

    '''if binary:
        #Dictionaires for converting call/put and bid/ask to 0 and 1
        cp = {"C": 0, "P": 1}
        ba = {"B": 0, "A": 1}

        #with open(filename, 'ab') as file:
            #file.write(struct.pack('iiifi', time, cp[right], ba[side], price, strike))

    elif not binary:
        try:
            with pd.ExcelWriter(filename, engine='openpyxl', mode = 'a') as writer:
                df.to_excel(writer, sheet_name=str(df.strike))
        except FileNotFoundError:
            with pd.ExcelWriter(filename) as writer:
                df.to_excel(writer)'''
    

def file_merge(out_filepath: str, dl_filepath: str, binary: bool) -> None:
    """
    Mrges files together of the given directory into an output binary or Excel file.
    
    Parameters
    ----------
    out_filepath: path of merged ouput file
    dl_filepath: path to folder of files (.parquet) to merge
    binary: True if binary (parquet) file, False for xlsx
    """
    original_dir = os.getcwd()

    if binary:
        SCHEMA = pa.schema([
            ('CallBid', pa.float64()),
            ('CallAsk', pa.float64()),
            ('PutBid', pa.float64()),
            ('PutAsk', pa.float64())
        ])

        with pq.ParquetWriter("intraday.parquet", schema=SCHEMA, compression='snappy') as writer:
            os.chdir("dl")

            for temp_file in glob.glob("*.parquet"):
                temp_df = pd.read_parquet(temp_file)
                table = pa.Table.from_pandas(temp_df)
                writer.write_table(table)

    else:
        with pd.ExcelWriter(out_filepath, engine='openpyxl') as writer:
            os.chdir(dl_filepath)
            
            for file in glob.glob("*.parquet"):
                strike: str = file.split('.')[0]

                # Read from parquet file
                df = pd.read_parquet(file)
                df.to_excel(writer, sheet_name=strike, header=False, index=False)

        '''with pd.ExcelWriter(out_filepath, engine='openpyxl') as writer:
            os.chdir(dl_filepath)
            
            for file in glob.glob("*.bin"):
                strike: str = file.split('.')[0]

                # Read from binary file
                data_array: np.ndarray = np.fromfile(file, dtype=float)
                
                # Reshape to be (seconds in 6.5 hours, 4) for 4 combinations of Put/Call and Bid/Ask)
                data_array = data_array.reshape((-1, 4))

                # Convert back to DataFrame
                df = pd.DataFrame(data_array)
                df.to_excel(writer, sheet_name=strike, header=False, index=False)'''

    os.chdir(original_dir)


def get_time_intervals(date: datetime, interval_length: int, time_unit: str, starting_time: datetime = None, ending_time: datetime = None) -> pd.DatetimeIndex:
    """
    Returns a list of time intervals between a given starting and end time (both inclusive).  
    Start and end times by default are 9:30 AM and 4:00 PM.

    Parameters
    ----------
    date: date to get intervals from
    interval_length: Time Interval
    time_unit: https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timeseries-offset-aliases
    starting_time: start time
    ending_time: end time
    """
    # Valid timestamps (Every 30 mins of the trading day (inclusive))
    intervals = pd.date_range(start=datetime(date.year, date.month, date.day, 9, 30, 0), end=datetime(date.year, date.month, date.day, 16, 0, 0), freq=f'{interval_length}{time_unit}')

    # Check if starting time is valid/assign default value of 9:30
    if starting_time is None:
        starting_time = datetime(date.year, date.month, date.day, 9, 30, 0)
    elif starting_time not in intervals or starting_time == intervals[-1]:
        raise SyntaxError("starting_time must be every 30 mins of the trading day (i.e. 9:30, 10:00, 10:30 ... 15:30).")
    
    # Check if ending time is valid/assign default value of 16:00
    if ending_time is None:
        ending_time = datetime(date.year, date.month, date.day, 16, 0, 0)
    elif ending_time not in intervals or ending_time == intervals[0]:
        raise SyntaxError("ending_time must be every 30 mins of the trading day (i.e. 10:00, 10:30 ... 15:30, 16:00).")

    # Check if ending time is before or equal to starting time
    if ending_time <= starting_time:
        raise SyntaxError("ending_time must be later than starting_time.")

    # Update intervals accordingly if needed
    if starting_time != datetime(date.year, date.month, date.day, 9, 30, 0) or ending_time != datetime(date.year, date.month, date.day, 16, 0, 0):
        intervals = pd.date_range(start=starting_time, end=ending_time, freq='30min')

    return intervals


def round_to_multiple(x: float, base: int) -> int:
    """
    Returns 'x' rounded to the nearest multiple of 'base'.

    Parameters
    ----------
    x: number to round
    base: multiple to round to
    """
    return base * round(x/base)


def create_sublist(list: list, n: int) -> list: 
    """
    Returns sublists of 'list' by grouping elements in groups of 'n'.
    If |list| not divisible by n, the last sublist will have a cardinality less than n

    Parameters
    ----------
    list: list to divide into sublists
    n: number of elements in each sublist
    """
    return [list[i:i + n] for i in range(0, len(list), n)]


def get_strike_range(number_of_strikes: int, opening_strike: int, starting_strike: int = None, ending_strike: int = None) -> range:
    """
    Returns the range of strike prices 'number_of_strikes' +/- 'opening_strike' or just between 'starting_strike' and 'ending_strike'. 

    Parameters
    ----------
    number_of_strikes: Number of strikes above and below the opening price to get
    opening_strike: Closest strike price at market open
    starting_strike: Custom lower bound strike
    ending_strike: Custom upper bound strike
    """
    if starting_strike is None:
        starting_strike = opening_strike - 5*number_of_strikes
    else:
        starting_strike = round_to_multiple(starting_strike, 5)

    if ending_strike is None:
        ending_strike = opening_strike + 5*number_of_strikes
    else:
        ending_strike = round_to_multiple(ending_strike, 5)

    if starting_strike > ending_strike:
        raise SyntaxError("starting_strike is greater than ending_strike")

    return range(starting_strike, ending_strike, 5)


def create_folder(name: str) -> None:
    """
    Creates a folder of specified name.

    Parameters
    ----------
    name: Name of folder to create
    """
    try:
        os.mkdir(name)
    except FileExistsError:
        pass


def get_data(out_filename: str, date: datetime, binary: bool, number_of_strikes: int = 30,
             starting_strike: int = None, ending_strike:int = None, starting_time: datetime = None, ending_time: datetime = None) -> None:
    """
    Function that gets all all options data for the SPX at 1 second intervals on a given date, then writes to a file.
    Splits the data into several files, then combines them at the end so that if a crash occurs, can continue from a specified file.

    Parameters
    ----------
    out_filename: output filename (without extension)
    date: date to get data of
    binary: True for output file to be .parquet file, False for .xlsx file
    number_of_strikes: number of strikes +/- the opening price to get the data of - default = 30
    
    starting_strike: Specific strike to start at (Must be less than ending_strike) - default = number_of_strikes * 5 - opening price
    ending_strike: Specific strike to start at (Must be less than ending_strike) - default = number_of_strikes * 5 + opening price
    starting_time: Specific time to start at (Must be less than ending_strike) - default = 9:30 AM EST
    ending_time: Specific time to start at (Must be less than ending_strike) - default = 4:00 PM EST
    """
    PRICE_TYPES: list[str] = ["CallBid", "CallAsk", "PutBid", "PutAsk"]

    # Add file extension
    out_filename += ".parquet" if binary else ".xlsx"

    # Create log file
    logfile = log("log.txt")

    # Connect to TWS
    try:
        ib = IB()
        ib.connect('127.0.0.1', 7497, clientId=1)
    except ConnectionRefusedError:
        logfile.write("ERROR: Not Connected to TWS API")
        raise ConnectionError("You are not connected to TWS API.")
    
    # Create time intervals (30 mins apart)
    intervals: pd.DatetimeIndex = get_time_intervals(date, 30, "min", starting_time, ending_time)

    # Get opening price of SPX
    date = date.replace(hour=9, minute=40)
    open_price: float = get_open_price(ib, date)
    logfile.write(f"FETCH: SPX Opening = {open_price}")

    # Round opening to nearest multiple of 5
    open_strike: int = round_to_multiple(open_price, 5)
    logfile.write(f"FETCH: SPX Opening Strike = {open_strike}")
    
    # Get strike prices to capture data from (NUM_OF_STRIKES +/- opening value if not custom interval)
    strike_range: range = get_strike_range(number_of_strikes, open_strike, starting_strike, ending_strike)
    logfile.write(f"FETCH: Strike Range = {strike_range[0]}-{strike_range[-1]}")

    # Sublists of 15 strikes each, due to rate limit
    strike_groups: list[list] = create_sublist(strike_range, 15)

    # Create data loaded(dl) subfile for temporary storage of files
    create_folder("dl")

    for start_interval, end_interval in zip(intervals[:-1], intervals[1:]):                             # Data of every 30 mins
        for strike_group in strike_groups:                                                              # Groups of 15 (or less) strikes
            for strike in strike_group:                                                                 # Each of the 15 strikes
                current_filepath: str = os.path.join("dl", str(strike) + ".parquet")

                # Clear files if starting from 9:30 AM
                if start_interval == start_interval.replace(hour=9, minute=30):
                    open(current_filepath,'w').close()

                # Create empty dataframe with rows of every second of the 30 min interval and columns of all 4 combinations of Put/Call and Bid/Ask
                seconds: pd.DatetimeIndex = pd.date_range(start_interval, periods=1800, freq='s', tz='US/Eastern')
                df = pd.DataFrame(0.0, index=seconds, columns=PRICE_TYPES)

                for price_type in PRICE_TYPES:                                                          # Prices for all 4 combinations of Put/Call and Bid/Ask
                    data: pd.DataFrame = fetch_data(ib, strike, price_type, end_interval)               # Get data at 1 second intervals
                    df.update(data)                                                                     # Update the dataframe

                file_write(df, current_filepath)

                logfile.write(f"FINISHED: {strike} up to {end_interval.strftime('%H:%M %p')}.")

                if strike != strike_group[-1] and strike_group != strike_groups[-1] and end_interval != intervals[-1]:
                    logfile.write(f"NEXT: {strike+5} from {start_interval.strftime('%H:%M %p')} to {end_interval.strftime('%H:%M %p')}.")

            time.sleep(610)                                                                             # 10 min cooldown after every 15 strikes

    # Merge all files together and delete them
    logfile.write(f"UPDATE: Creating output file: {out_filename}")
    file_merge(out_filename, "dl", binary)
    logfile.write(f"DONE: All data gathered")

    # Disconnect from IB
    ib.disconnect()


## For Testing
def main() -> None:
    FILENAME = 'intraday'
    DATE = datetime.now()
    IS_BINARY = True

    tik = time.time()
    start = datetime.now()
    print(f"start time = {start}")

    get_data(FILENAME, DATE, IS_BINARY)

    end = datetime.now()
    print(f"end time = {end}")

    tok = time.time()
    print(f"Runtime: {tok-tik} seconds")


if __name__ == "__main__":
    main()