"""
This module contains a function (order_combo) to order an iron condor
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

# Connect to IB
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

def get_contract(strike: float, right: str) -> Option:
    """
    Helper function that qualifies and returns the SPXW 0DTE contract with the given strike and right.

    Parameters
    ----------
    strike: Strike price of the option
    right: 'P' or 'C'
    """
    contract: Option = Option('SPXW', date.today().strftime('%Y%m%d'), strike, right, 'SMART', tradingClass='SPXW')
    ib.qualifyContracts(contract)

    return contract

def order_combo(call_spread: tuple[float, float, float], put_spread: tuple[float, float, float], nof_lot: int, stop_trigger_price: float, stop_limit_price: float) -> int:
    """
    Submits an combo spread order and returns the order ID.

    Parameters
    ----------
    call_spread: tuple of call spread strike prices
    put_spread: tuple of put spread strike prices
    nof_lot: number of lots to order
    stop_trigger_price: stop price
    stop_limit_price: limit price
    """
    long_put_strike, short_put_strike, short_call_strike, long_call_strike = sorted(call_spread[:2] + put_spread[:2])

    legs = [
        ComboLeg(conId=get_contract(long_call_strike, 'C').conId, ratio=1, action='BUY', exchange='SMART'), 
        ComboLeg(conId=get_contract(short_call_strike, 'C').conId, ratio=1, action='SELL', exchange='SMART'),
        ComboLeg(conId=get_contract(short_put_strike, 'P').conId, ratio=1, action='SELL', exchange='SMART'),
        ComboLeg(conId=get_contract(long_put_strike, 'P').conId, ratio=1, action='BUY', exchange='SMART')
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

    """# Define the stop-loss order
    stop_loss_order = Order()
    stop_loss_order.action = 'BUY'
    stop_loss_order.orderType = 'STP LMT' if stop_limit_price is not None else 'STP'
    stop_loss_order.totalQuantity = nof_lot
    stop_loss_order.auxPrice = stop_trigger_price
    if stop_limit_price:
        stop_loss_order.lmtPrice = stop_limit_price"""

    print(parent_order)
    print()
    #print(stop_loss_order)

    # Attach stop-loss order to the parent order
    #stop_loss_order.parentId = parent_order.orderId

    # Place the orders
    trade = ib.placeOrder(combo, parent_order)

    # Keep the connection open until orders are filled
    ib.sleep(5)
    
    order_id = trade.order.orderId
    print(f"order ID = {order_id}")

    ib.disconnect()

    return order_id


## For testing:
def main() -> None:
    call_spread = (5345.0, 5355.0, 1.3750000000000002)
    put_spread = (5305.0, 5295.0, 1.0750000000000002)

    order_combo(call_spread, put_spread, nof_lot=1, stop_trigger_price=-1.0, stop_limit_price=-2.0)

if __name__ == '__main__':
    main()