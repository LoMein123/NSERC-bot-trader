"""
This module reports sell or buy executions.
"""
from ib_insync import *

def get_executions() -> list[dict]:
    """
    Returns information about today's executions [action, fin instrument, price, time, commission, quantity].  
    Refer to interactive broker's 'trade history' window.
    """
    # Connect to IB
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)

    executions: list[dict] = []

    fills = ib.fills()

    for fill in fills:
        print(f"{fill}")
        print(f"Type: {type(fill.contract)}")
        print(f"Price: {fill.execution.price}")
        print(f"Commssion: ${round(fill.commissionReport.commission, 2)}\n")
        executions.append({'Action': fill.execution.side, 
                           'Fin Instrument': fill.contract.symbol,
                           'Price': fill.execution.price,
                           'Time': fill.execution.time,
                           'Commission': round(fill.commissionReport.commission, 2),
                           'Quantity': fill.execution.cumQty}
        )  

    ib.disconnect()

    return executions


def main() -> None:
    executions = get_executions()

    for order in executions:
        print(order)

if __name__ == "__main__":
    main()