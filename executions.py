"""
This module reports sell or buy executions.
"""
from ib_insync import *

def main() -> None:
    # Connect to IB
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)

    fills = ib.fills()

    print("==== loop fills =====")
    for fill in fills:
        print(f"{fill}")

    ib.disconnect()

if __name__ == "__main__":
    main()