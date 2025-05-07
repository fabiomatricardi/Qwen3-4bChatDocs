# Chat with an intelligent assistant in your terminal  with Qwen_Qwen3-4B-Q4_K_L.gguf
# model served in another terminal window with llama-server
from openai import OpenAI
import sys
from time import sleep
import rich
#from rich.prompt import Confirm
import pypdf
import tiktoken
from easygui import fileopenbox

STOPS = ['<|im_end|>']
COUNTERLIMITS = 16  #an even number

def countTokens(text):
    if text is None: return 0
    encoding = tiktoken.get_encoding("cl100k_base")
    numoftokens = len(encoding.encode(str(text)))
    return numoftokens


def PDFtoText(pdffile):
    # try to read the PDF and write it into a txt file, same name but .txt extension
    # code based on my repo https://github.com/fabiomatricardi/PDF-to-Text
    try:
        reader = pypdf.PdfReader(pdffile)
        text = ""
        page_count = len(reader.pages)
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text: text += page_text + "\n"
        a = text.strip()
        textfile = a.replace('\n\n','')
        print('Creating text file...')
        print(f"Parsed from PDF {page_count} pages of text\nA total context of {countTokens(textfile)} tokens ")
        return textfile
    except Exception as e:
        print(f"⚠️ Error reading PDF {pdffile}: {e}")


#Menu options like Llamafile
helpcommands = """
/clear      clear the chat history and reset flags, including RAG
/multi      multi line input Enter your text (end input with Ctrl+D on Unix or Ctrl+Z on Windows)
/help       display help message and commands
/rag        load a pdf from your pc and start RAG session
/exit       end program
/think      activate thinking mode
/no_think   deactivate thinking mode
"""

# ASCII ART FROM https://asciiart.club/
print("""

HI QWEN3
    
---
""")
# Point to the local server
client = OpenAI(base_url="http://localhost:8080/v1", api_key="not-needed")
print("Ready to Chat with Qwen3-4B  Context length=32k...")
print(helpcommands)
print("\033[0m")  #reset all
history = []
print("\033[92;1m")


multilines = False
rag = False
context = ''
thiking = False
counter = 0
firstturn = True  # used for the RAG prompts

while True:
    # trim the chat history if above the COUNTERLIMITS value
    if counter > COUNTERLIMITS:
        chathistory = history[-14:]
        print('⚠️ You reached maximum chat history')  
    else:
         chathistory = history     
    userinput = ""
    ################################# Single line case
    if not multilines:
        print("\033[91;1m")  #red
        lines = input('> ')
        # HELP COMMANDS SESSION
        if lines == '/clear':
            print('🗑️ clearing chat history, reset flags and back to single line input')
            history = []
            rag = False
            thiking = False
            counter = 0
            multilines = False
            context = ''
        elif lines == '/multi':
            print('Starting multi line input Enter your text (end input with Ctrl+D on Unix or Ctrl+Z on Windows)')
            multilines = True
        elif lines == '/help':
            print(helpcommands)
        elif lines == '/exit':
            print("\033[0mBYE BYE!")
            break   
        elif lines == '/think':
            print("Activating Thinking mode...")
            thiking = True  
        elif lines == '/no_think':
            print("DE-Activating Thinking mode...")
            thiking = False 
        elif lines == '/rag':
            print("Upload your file and start chatting with it...")
            pdffile = fileopenbox(msg='Pick your PDF', default='*.pdf')
            context = PDFtoText(pdffile)
            rag = True 
            preparedText = f"""Read the provided text and follow the instructions. 
                           
Write a short summary and a concise Table of Contents of the text. When you are done say "Do you have any other questions?".  
Format your reply as follows:

SHORT SUMMARY:

CONCISE TABLE OF CONTENTS:

[start of provided text]
{context} 
[end of provided text]                       
/no_think

"""
            # CALL local API endpoint
            history = []
            chathistory = [] 
            history.append({"role": "user", "content": preparedText})
            chathistory.append({"role": "user", "content": preparedText})         
            print("\033[92;1m") #green

            completion = client.chat.completions.create(
                model="local-model", # this field is currently unused
                messages=chathistory,
                temperature=0.3,
                frequency_penalty  = 1.6,
                max_tokens = 1800,
                stream=True,
                stop=STOPS)
            new_message = {"role": "assistant", "content": ""}
            # print the streming text
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end="", flush=True)
                    new_message["content"] += chunk.choices[0].delta.content
            history.append(new_message)  
            chathistory.append(new_message) 
            counter += 1  
        ##### RAG AND NORMaL CHAT SESSION
        else:
            if not thiking:
                userinput = lines + "/no_think \n"
            else:
                userinput = lines + "/think \n"
            # CALL local API endpoint
            history.append({"role": "user", "content": userinput})
            chathistory.append({"role": "user", "content": userinput})
            print("\033[92;1m") #green

            completion = client.chat.completions.create(
                model="local-model", # this field is currently unused
                messages=chathistory,
                temperature=0.3,
                frequency_penalty  = 1.6,
                max_tokens = 1800,
                stream=True,
                stop=STOPS)
            new_message = {"role": "assistant", "content": ""}
            # print the streming text
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end="", flush=True)
                    new_message["content"] += chunk.choices[0].delta.content
            history.append(new_message)  
            chathistory.append(new_message) 
            counter += 1  
      


    ################################# Multi lines case
    else:
        print("\033[91;1m")  #red
        lines = sys.stdin.readlines()
        # HELP COMMANDS SESSION
        if lines[0].strip().lower() == '/clear':
            print('🗑️ clearing chat history, reset flags and back to single line input')
            history = []
            rag = False
            thiking = False
            counter = 0
            multilines = False
            context = ''
        elif lines[0].strip().lower() == '/help':
            print(helpcommands)
        elif lines[0].strip().lower() == '/exit':
            print("\033[0mBYE BYE!")
            break   
        elif lines[0].strip().lower() == '/think':
            print("Activating Thinking mode...")
            thiking = True  
        elif lines[0].strip().lower() == '/no_think':
            print("DE-Activating Thinking mode...")
            thiking = False 
        elif lines[0].strip().lower() == '/rag':
            print("Upload your file and start chatting with it...")
            pdffile = fileopenbox(msg='Pick your PDF', default='*.pdf')
            context = PDFtoText(pdffile)
            rag = True 
            preparedText = f"""Read the provided text and follow the instructions. 
                           
Write a short summary and a concise Table of Contents of the text. When you are done say "Do you have any other questions?".  
Format your reply as follows:

SHORT SUMMARY:

CONCISE TABLE OF CONTENTS:

[start of provided text]
{context} 
[end of provided text]                       
/no_think

"""
            # CALL local API endpoint
            history = []
            chathistory = [] 
            history.append({"role": "user", "content": preparedText})
            chathistory.append({"role": "user", "content": preparedText})
            print("\033[92;1m") #green

            completion = client.chat.completions.create(
                model="local-model", # this field is currently unused
                messages=chathistory,
                temperature=0.3,
                frequency_penalty  = 1.6,
                max_tokens = 1800,
                stream=True,
                stop=STOPS)
            new_message = {"role": "assistant", "content": ""}
            # print the streming text
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end="", flush=True)
                    new_message["content"] += chunk.choices[0].delta.content
            history.append(new_message)  
            chathistory.append(new_message) 
            counter += 1      
        ##### RAG AND NORMaL CHAT SESSION
        else:
            if not thiking:
                for line in lines:
                    userinput += line + "\n"  
                userinput += "/no_think \n"
            else:
                for line in lines:
                    userinput += line + "\n"
                userinput += "/think \n"   
            
            # CALL local API endpoint
            history.append({"role": "user", "content": userinput})
            chathistory.append({"role": "user", "content": userinput})
            print("\033[92;1m") #green

            completion = client.chat.completions.create(
                model="local-model", # this field is currently unused
                messages=chathistory,
                temperature=0.3,
                frequency_penalty  = 1.6,
                max_tokens = 1800,
                stream=True,
                stop=STOPS)
            new_message = {"role": "assistant", "content": ""}
            # print the streming text
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end="", flush=True)
                    new_message["content"] += chunk.choices[0].delta.content
            history.append(new_message)  
            chathistory.append(new_message) 
            counter += 1  
         





