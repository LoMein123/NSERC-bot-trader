"""
This module reports sell or buy executions.
"""
from ib_insync import *

def get_executions(ib: IB) -> list:
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

    return executions

def main() -> None:
    # Connect to IB
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)

    executions = get_executions(ib)

    for order in executions:
        print(order)

    ib.disconnect()

if __name__ == "__main__":
    main()