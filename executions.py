from ib_insync import *

ib: IB = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

#executions = ib.executions()
fills = ib.fills()

#print(executions)

print("==== loop fills =====")
for fill in fills:
    print(f"{fill}")

ib.disconnect()