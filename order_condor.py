"""
This module contains a function (order_condor) to order an iron condor
given the call and put spreads, number of lots, stop trigger price, 
and stop limit price.

# Example Iron Condor
# long_call_strike: 120
# short_call_strike: 110
# Market Value: 105
# short_put_strike: 100
# long_put_strike: 90
"""
from ib_insync import *
from datetime import date
from find_spreads import get_spreads

def get_contract(ib: IB, strike: float, right: str) -> Option:
    """
    Helper function that qualifies and returns the SPXW 0DTE contract with the given strike and right.

    Parameters
    ----------
    ib: Interactive brokers object
    strike: Strike price of the option
    right: 'P' or 'C'
    """
    contract: Option = Option('SPXW', date.today().strftime('%Y%m%d'), strike, right, 'SMART', tradingClass='SPXW')
    ib.qualifyContracts(contract)

    return contract

def order_condor(call_spread: tuple[float], put_spread: tuple[float], nof_lot: int, 
                 stop_trigger_price: float, stop_limit_price: float, 
                 stop_loss_type: str, stop_loss_trigger_price: float, stop_loss_limit_price: float = None) -> int:
    """
    Submits an combo spread order with stop loss and returns the order ID.

    Parameters
    ----------
    call_spread: Tuple of call spread strike prices
    put_spread: Tuple of put spread strike prices
    nof_lot: Number of lots to order
    stop_trigger_price: Parent order's stop price
    stop_limit_price: Parent order's limit price
    stop_loss_type: Stop loss order type ('STP' or 'STP LMT')
    stop_loss_trigger_price: Stop loss's trigger price
    stop_loss_limit_price: Stop loss's limit price - default None
    """
    # Connect to IB
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)

    # Unpack strike prices
    long_put_strike, short_put_strike, short_call_strike, long_call_strike = sorted(call_spread[:2] + put_spread[:2])

    legs = [
        ComboLeg(conId=get_contract(ib, long_call_strike, 'C').conId, ratio=1, action='BUY', exchange='SMART'), 
        ComboLeg(conId=get_contract(ib, short_call_strike, 'C').conId, ratio=1, action='SELL', exchange='SMART'),
        ComboLeg(conId=get_contract(ib, short_put_strike, 'P').conId, ratio=1, action='SELL', exchange='SMART'),
        ComboLeg(conId=get_contract(ib, long_put_strike, 'P').conId, ratio=1, action='BUY', exchange='SMART')
    ]

    # Combo order contract
    combo = Contract()
    combo.symbol = 'SPX'
    combo.secType = 'BAG'
    combo.currency = 'USD'
    combo.exchange = 'SMART'
    combo.comboLegs = legs

    # Define the parent combo order (buy for credit stop limit)
    parent_order = StopLimitOrder(
        action = 'BUY',
        totalQuantity = nof_lot,
        lmtPrice = stop_limit_price,
        stopPrice = stop_trigger_price
    )

    # Define the stop loss order
    if stop_loss_type == "STP LMT":
        stop_loss_order = StopLimitOrder(
            action = 'SELL',
            totalQuantity = nof_lot,
            lmtPrice= stop_loss_limit_price,
            stopPrice = stop_loss_trigger_price
        )
    elif stop_loss_type == "STP":
        stop_loss_order = StopOrder(
            action = 'SELL',
            totalQuantity = nof_lot,
            stopPrice = stop_loss_trigger_price
        )
    else:
        raise ValueError("stop_loss_type must be \'STP\' or \'STP LMT\'.")
                         
    # Attach the stop loss order to the parent order
    stop_loss_order.parentId = parent_order.orderId

    # Place the parent order
    parent_trade = ib.placeOrder(combo, parent_order)
    ib.sleep(1)
    
    # Get the parent order ID and place the stop loss order
    stop_loss_order.parentId = parent_trade.order.orderId
    ib.placeOrder(combo, stop_loss_order)

    order_id = parent_trade.order.orderId
    print(f"order ID = {order_id}")

    ib.disconnect()

    return order_id


## For testing:
def main() -> None:
#    call_spread, put_spread = get_spreads(width=10, time="3:30", entry_credit=1, nof_lot=1)

 #   if call_spread is None or put_spread is None:
  #      raise TypeError("Spread Not Found")

    call_spread = (5520, 5530)
    put_spread = (5485, 5495)

    order_condor(call_spread, put_spread, nof_lot=1, 
                stop_trigger_price=-1.0, stop_limit_price=-1.0, 
                stop_loss_type="STP LMT", stop_loss_trigger_price=-3.0, stop_loss_limit_price=-0.9)

if __name__ == '__main__':
    main()