import requests
import asyncio
from openai import OpenAI
from functools import reduce


class LMStudioSession:
    def __init__(self, address, systemPrompt, port = 1234, timeout = 10, config = "", mode = "API"):
        print("creating instance")
        self.address = None
        self.client = None
        self.operatingMode = mode
        self.systemPrompt = systemPrompt
        self.messages = [self.generateSystemPromptLine(systemPrompt)]
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
                "model": 'local mdoel'
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
        output = {"role": "system", "content": prompt}
        return(output)
    
    
    def clearMessageHistory(self):
        self.messages = []
        prompt = self.generateSystemPromptLine(self.systemPrompt)
        self.messages.append(prompt)


    def sendMessage(self, message): #
        payload = {}
        payload.update(self.config)
        taggedMessage = {"role": "user", "content": message}        
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
        print("is actually waiting? " + str(output))
        
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
    

    async def receiveMessage(self): #in theory, based on the implementation of LM Studio, reponses should always be returned in the same order as messages are sent
        output = {}
        if(self.isWaitingForResponse() or self.hasMessagesReady()):
            while(not self.hasMessagesReady()):
                await asyncio.sleep(0.2)
            
            handle = ""            
            for (index, element) in enumerate(self.messageQueue):
                handle = element
                if(handle['handle'].done()):
                    self.messageQueue.pop(index)
                    break;

            self.messages.append(handle['input'])
            message = self.decodeMessageContent(handle)
            self.messages.append(message)
            output = (handle, message)
        else:
            output = "no output"

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
            'role': message.role,
            'content': message.content,
            'function call': message.function_call,
            'tool calls': message.tool_calls
        }
        return(output)