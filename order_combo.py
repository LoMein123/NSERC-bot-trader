"""
This module contains a function (order_combo_profit_taker) to order a multi-leg
combo position and attach a stop loss order.
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

def order_combo_profit_taker(call_spread: tuple[float], put_spread: tuple[float], nof_lot: int, stop_trigger_price: float, stop_limit_price: float, stop_loss_trigger_price: float, stop_loss_limit_price: float = None) -> int:
    """
    Submits an combo spread order with stop loss and returns the order ID.

    Parameters
    ----------
    call_spread: tuple of call spread strike prices
    put_spread: tuple of put spread strike prices
    nof_lot: number of lots to order
    stop_trigger_price: parent order's stop price
    stop_limit_price: parent order's limit price
    stop_loss_trigger_price: stop loss's trigger price
    stop_loss_limit_price: stop loss's limit price - default None; set if you want the stop loss to be a stop limit order
    
    Returns
    ----------
    Order ID of the placed order
    """
    # Connect to IB
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=12)

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
    if stop_loss_limit_price:
        stop_loss_order = StopLimitOrder(
            action = 'SELL',
            totalQuantity = nof_lot,
            lmtPrice= stop_loss_limit_price,
            stopPrice = stop_loss_trigger_price
        )
    else:
        stop_loss_order = StopOrder(
            action = 'SELL',
            totalQuantity = nof_lot,
            stopPrice = stop_loss_trigger_price
        )

    # Attach the stop loss order to the parent order
    stop_loss_order.parentId = parent_order.orderId

    # Place the parent order
    parent_trade = ib.placeOrder(combo, parent_order)

    # Keep the connection open until orders are filled
    ib.sleep(5)
    
    # Get the parent order ID and place the stop loss order
    parent_order_id = parent_trade.order.orderId
    stop_loss_order.parentId = parent_order_id
    stop_loss_trade = ib.placeOrder(combo, stop_loss_order)

    order_id = parent_trade.order.orderId
    print(f"order ID = {order_id}")

    ib.disconnect()

    return order_id


## For testing:
def main() -> None:
    call_spread, put_spread = get_spreads(width=10, time="3:30", entry_credit=1, nof_lot=1)

    if call_spread is None or put_spread is None:
        raise TypeError("Spread Not Found")

    order_combo_profit_taker(call_spread, put_spread, nof_lot=1, 
                stop_trigger_price=-1.0, stop_limit_price=-1.0, 
                stop_loss_trigger_price=-3.0, stop_loss_limit_price=-0.9)

if __name__ == '__main__':
    main()