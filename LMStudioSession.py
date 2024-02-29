import requests
import asyncio
from openai import OpenAI
from functools import reduce
import graphviz


class LMStudioSession: #maybe return a numeric message ID as a sendMessage identifier?  could be lighter weight and more reliable?
    def __init__(self, address, systemPrompt, port = 1234, timeout = 60, config = "", mode = "API", existingChatHistory = ""):
        print("creating instance")
        self.address = None
        self.client = None
        self.operatingMode = mode
        self.systemPrompt = systemPrompt
        self.sentID = 0
        self.receivedID = 0
        self.transactionID = 0
        self.eventID = 0
        self.messages = [self.generateSystemPromptLine(systemPrompt)] if existingChatHistory == "" else existingChatHistory
        self.messageHandle = "empty"
        self.messageQueue = []        
        self.timeout = timeout
        self.config = {}
        
        print("configured some variables")

        if(config != ""):
            self.config = config
        else:
            self.config = {
                "temperature": 0.7, 
                "max_tokens": -1,
                "stream": False,
                "model": 'local model'
            }

        if(self.operatingMode == "API"):
            self.address = "http://" + address + ":" + port + "/v1"
            self.sendMessageHelper = self.sendMessageHelperAPI
            self.decodeMessageContent = self.decodeMessageContentHelperAPI
            self.client = OpenAI(base_url=self.address, api_key="not-needed")
        elif(self.operatingMode == "CURL"):
            self.address = "http://" + address + ":" + port + "/v1/chat/completions"
            self.sendMessageHelper = self.sendMessageHelperCURL
            self.decodeMessageContent = self.decodeMessageContentHelperCURL
        else:
            raise ConnectionRefusedError

        print("finished configuring variables")
    

    def generateSystemPromptLine(self, prompt):
        output = {
            "sent id": self.sentID,
            "received id": -1,
            "transaction id": self.transactionID,
            "event id": self.eventID,
            "role": "system",
            "content": prompt,
            "function call": '',
            "tool calls": ''
            }
        return(output)
    
    
    def clearMessageHistory(self):
        if((not self.isWaitingForResponse()) and (not self.hasMessagesReady())):
            self.messages = [self.generateSystemPromptLine(self.systemPrompt)]        
            self.sentID = 0
            self.receivedID = 0
            self.transactionID = 0
        else:
            raise Exception("cannot clear message history while waiting for messages")

    
    def getChatHistory(self):
        return(self.messages)
    

    def getFormattedChatHistory(self):
        output = reduce(lambda x, y: x + "\n\n" + y['role'] + " - " + str(y['event id']) +  + " : " + y['content'], self.messages, "")
        output = output[1:]
        return(output)


    def sendMessage(self, message): #
        payload = {}
        payload.update(self.config)
        self.sentID = self.sentID + 1
        self.transactionID = self.transactionID + 1
        self.eventID = self.eventID + 1
        taggedMessage = {
            "sent id": self.sentID,
            "received id": -1,
            "transaction id": self.transactionID,
            "event id": self.eventID,
            "role": "user",
            "content": message,
            "function call": '',
            "tool calls": ''
            }
        payload['messages'] = self.messages.copy()
        payload['messages'].append(taggedMessage)

        print(payload)
        messageHandle = asyncio.create_task(self.sendMessageHelper(payload))
        buffer = {
          'handle': messageHandle,
          'input': taggedMessage
        }
        self.messageQueue.append(buffer)
        return(buffer)
    

    def isWaitingForResponse(self): #
        output = reduce(lambda x, y: x or (not y['handle'].done()), self.messageQueue, False)        
        return(output)
    

    def hasMessagesReady(self):
        output = reduce(lambda x, y: x or y['handle'].done(), self.messageQueue, False)
        return(output)
    

    def allMessagesReady(self):
        output = reduce(lambda x, y: x and y['handle'].done(), self.messageQueue, True)
        return(output)
    

    def hasMessagesInQueue(self):
        output = len(self.messageQueue) > 0
        return(output)
    

    async def receiveAllMessages(self):
        output = []
        while(self.isWaitingForResponse() or self.hasMessagesReady()):
            buffer = self.receiveMessage()
            output.append(buffer)
        
        return(output)


    async def receiveMessage(self): #in theory, based on the implementation of LM Studio, reponses should always be returned in the same order as messages are sent
        output = {}
        print("receive attempt")
        if(self.isWaitingForResponse() or self.hasMessagesReady()):
            while(not self.hasMessagesReady()):
                print("waiting")
                await asyncio.sleep(0.2)
                print("cycled")
            
            print("done waiting")
            handle = ""            
            for (index, element) in enumerate(self.messageQueue):
                handle = element
                if(handle['handle'].done()):
                    self.messageQueue.pop(index)
                    break;
                        
            self.messages.append(handle['input'])
            message = self.decodeMessageContent(handle)
            message = self.receiveMessageHelper(message, handle)
            self.messages.append(message)
            output = (handle, message)
        else:
            output = "no output"

        return(output)
    
    
    def receiveMessageHelper(self, message, context):
        output = message
        self.eventID = self.eventID + 1
        self.receivedID = self.receivedID + 1
        output['sent id'] = -1
        output['event id'] = self.eventID
        output['transaction id'] = context['input']['transaction id']
        output['receive id'] = self.receivedID        
        return(output)
    

    async def sendMessageHelperCURL(self, payload):
        output = requests.post(self.address, json = payload, timeout = self.timeout)
        return(output)
    

    async def sendMessageHelperAPI(self, payload):
        output = self.client.chat.completions.create(
            model=payload['model'], # this field is currently unused
            messages=payload['messages'],
            temperature=payload['temperature'],
        ) 
        return(output)   


    def decodeMessageContentHelperCURL(self, handle):
        outputBuffer = handle['handle'].result().json()
        output = outputBuffer['choices'][0]['message']
        output['function call'] = ""
        output['tool calls'] = ""
        return(output)
    

    def decodeMessageContentHelperAPI(self, handle):
        message = handle['handle'].result().choices[0].message
        output = {
            'sent id': self.sentID,
            'received id': -1,
            'transaction id': self.transactionID,
            'role': message.role,
            'content': message.content,
            'function call': message.function_call,
            'tool calls': message.tool_calls
        }
        return(output)