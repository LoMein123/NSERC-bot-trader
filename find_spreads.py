"""
This module contains a function to find a 0DTE put spread and 
a 0DTE call spread for the SPXW that matches the given width
and has mid-price matching the given entry credit
"""
from ib_insync import *
from datetime import date

def find_closest_midspread(market_price: float, spreads: list[tuple], right: str, saftey_zone: float = 0) -> tuple:
    """
    Returns the closest spread to the market price.
    Returns None if no spreads found.

    Parameters:
    - market_price: Current market price of SPX
    - spreads: List of spreads
    - right: "P" for put, "C" for call
    - saftey_zone: Buffer between market price and closest spread - default 0
    """
    valid_spreads: list = []

    for spread in spreads:
        strike1: float = spread[0]
        strike2: float = spread[1]

        if right == "P":    # Put
            # Check if strike prices are below market price
            if strike1 < (market_price-saftey_zone) and strike2 < (market_price-saftey_zone):
                valid_spreads.append(spread)

        elif right == "C":   # Call
            # Check if strike prices are above market price
            if strike1 > (market_price+saftey_zone) and strike2 > (market_price+saftey_zone):
                valid_spreads.append(spread)
        
        else:
            raise SyntaxError("P for put, C for call")

    print(f"Market price: {market_price}")
    print(f"Valid Spreads: {valid_spreads}")

    try:
        return valid_spreads[0]
    except IndexError:
        return None
                

def find_spreads(tickers: list[Ticker], width: float, entry_credit: float) -> tuple:
    """
    Function that finds

    :param tickers:
    :param width:
    :param entry_credit: 
    """
    
    # Create ticker lists
    call_tickers = [t for t in tickers if t.contract.right == 'C']
    put_tickers = [t for t in tickers if t.contract.right == 'P']


    call_spreads = find_spreads_in_list(call_tickers, 'call', width, entry_credit)
    put_spreads = find_spreads_in_list(put_tickers, 'put', width, entry_credit)

    return call_spreads, put_spreads


def mid_price(ticker: Ticker) -> float:
        """
        Function that returns the midprice of an option.

        Parameters: 
        - ticker: ticker object
        """
        print(f"ticker.contract.right={ticker.contract.right}")
        print(f"ticker.contract.strike={ticker.contract.strike}")
        print(f"ticker.bid={ticker.bid}")
        print(f"ticker.ask={ticker.ask}")
        
        return (ticker.bid + ticker.ask) / 2


def find_spreads_in_list(ticker_list: list[Ticker], right: str, width: float, entry_credit: float):
        """
        Helper function that finds all 
        """
        spreads = []
        ticker_dict = {ticker.contract.strike: ticker for ticker in ticker_list}

        for short_strike in ticker_dict:
            if right == 'call':
                long_strike = short_strike + width
            else:  # 'put'
                long_strike = short_strike - width

            if long_strike in ticker_dict:
                short_mid = mid_price(ticker_dict[short_strike])
                long_mid = mid_price(ticker_dict[long_strike])
                spread_mid = short_mid - long_mid

                spread_mid_rounded = round(spread_mid, 2)

                print(f"spread_mid, entry_credit = {spread_mid_rounded}, {entry_credit}")

                # Ensure that the spread_mid is a credit and meets the minimum entry_credit
                if spread_mid_rounded >= entry_credit:
                    spreads.append((short_strike, long_strike, spread_mid_rounded))
        return spreads


def get_spreads(width: float, time, entry_credit: float, nof_lot: int, upper_profit_zone: float = 0, lower_profit_zone: int = 0) -> tuple[tuple]:
    """
    Main function that returns 0DTE put spread and a 0DTE 
    call spread for the SPX that matches the given width
    and has mid-price matching the given entry credit that
    is closest to the market price at somet time.

    
    Parameters:
    width: Width of the spread
    time: Time to execute trade
    entry_credit: entry credit
    nof_lot: number of lots

    Returns
    ----------
    Tuple of spread strike prices
    """

    # Initialize IB connection
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)

    # Create contract for SPX
    spx = Index('SPX', 'CBOE')
    ib.qualifyContracts(spx)

    # Get current data
    ib.reqMarketDataType(1)

    # Get SPX market price
    [ticker] = ib.reqTickers(spx)
    print(f"\nticker={ticker}\n")
    spx_value = ticker.marketPrice()
    print(f"spx_value={spx_value}\n")

    # Get option chains
    chains = ib.reqSecDefOptParams(spx.symbol, '', spx.secType, spx.conId)
    print("Option Chains: ")
    print(util.df(chains))

    # Get SPXW trading on SMART
    chain = next(c for c in chains if c.tradingClass == 'SPXW' and c.exchange == 'SMART')
    print(f"\nchain={chain}\n")

    # Filter strikes within ±10 times the width points of the SPX value
    strikes = [strike for strike in chain.strikes if strike % 5 == 0 and (spx_value - 10*width) < strike < (spx_value + 10*width)]
    expiration = date.today().strftime('%Y%m%d')
    rights = ['P', 'C']
    print(f"\nFiltered strikes = {strikes}\n")

    #expirations = sorted(exp for exp in chain.expirations)[:1]
    #print(f"\nexpiration = {expirations}\n")

    # Create option contracts
    contracts = [Option('SPXW', expiration, strike, right, 'SMART', tradingClass='SPXW')
                for right in rights
                for strike in strikes]

    # Qualify contracts
    print("--- before ib.qualifyContracts ---")
    contracts = ib.qualifyContracts(*contracts)
    print("--- after ib.qualifyContracts ---")

    print(f"\nNumber of contracts = {len(contracts)}\n")
    print("Contracts: ")
    print(*contracts, sep = "\n")

    # Request tickers for all options
    tickers = ib.reqTickers(*contracts)
    print("\nTickers:")
    print(*tickers, sep = "\n")

    # Use the function to find the spreads
    short_call_strikes, short_put_strikes = find_spreads(tickers, width, entry_credit)
    print(f"Short Call Strikes: {short_call_strikes}")
    print(f"Short Put Strikes: {short_put_strikes}")

    short_call_strikes.sort(key=lambda x: x[2])
    short_put_strikes.sort(key=lambda x: x[2])
    print("====================")
    print(f"\nSorted Short Call Strikes closest to entry_credit: {short_call_strikes}")
    print(f"\nSorted Put Strikes closest to entry_credit: {short_put_strikes}")
    print("====================")

    closest_call_spread = find_closest_midspread(market_price=spx_value, spreads=short_call_strikes, right="C", saftey_zone=upper_profit_zone)
    closest_put_spread = find_closest_midspread(market_price=spx_value, spreads=short_put_strikes, right="P", saftey_zone=lower_profit_zone)

    print(f"\nMarket price: {spx_value}")
    print(f"Closest call: {closest_call_spread}")
    print(f"Closest put:  {closest_put_spread}")

    ib.disconnect()

    return closest_call_spread, closest_put_spread


## For testing:
def main() -> None:
    width = 10              # Spread width
    entry_credit = 1        # Entry credit
    nof_lot = 1             # Number of lots

    get_spreads(width, "3:30", entry_credit, nof_lot)

if __name__ == '__main__':
    main()