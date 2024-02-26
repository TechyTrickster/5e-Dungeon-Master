from openai import OpenAI
from LMStudioSession import LMStudioSession
import asyncio

async def test():
  #Point to the local server
  session = LMStudioSession("192.168.50.216", "Always answer in rhymes", timeout = 20, port = "1234", mode = "CURL")
  print("created session instance")
  session.sendMessage("introduce yourself")
  session.sendMessage("how are you doing?")
  session.sendMessage("how about that game last night?")
  session.sendMessage("do you like video games?")
  print("sent message")
  data0 = await session.receiveMessage()
  print("recieved response")
  print(data0)
  data1 = await session.receiveMessage()
  print("recieved another message")
  print(data1)
  data2 = await session.receiveMessage()
  print("recieved another message")
  print(data2)
  data3 = await session.receiveMessage()
  print("recieved another message")
  print(data3)



loop = asyncio.get_event_loop()
loop.run_until_complete(test())