"""
This module contains a function 'cancel_order' that cancels an order with the given order ID.
"""
from ib_insync import *

def cancel_order(order_id: int) -> bool:
    """
    Cancel an order with the given order ID and returns True if canceled successfully.

    Parameters:
    - order_id: The ID of the order to cancel.
    """
    # Initialize IB connection
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)

    # Find the order by order id
    orders = [order for order in ib.orders() if order.orderId == order_id]

    if not orders:
        return False
    
    # Cancel order
    order = orders[0]
    ib.cancelOrder(order)
    ib.sleep(1)

    ib.disconnect()
    
    return True


## For testing
if __name__ == "__main__":
    order_id = 5177
    if not cancel_order(order_id):
        print("Order not found")