"""
# Chat with an intelligent assistant in your terminal  with Qwen_Qwen3-1.7B-Q5_K_M.gguf
# model served in another terminal window with llama-server
# added support to llama-cpp server tokenizer to count tokens
# added parsing of <think></think>
# using jinja template for token counts 
# llama-server.exe -m Qwen_Qwen3-1.7B-Q5_K_M.gguf -c 16348 -ngl 0

Qwen Template: https://huggingface.co/Qwen/Qwen3-1.7B/blob/main/tokenizer_config.json
"""

from openai import OpenAI
import sys
from time import sleep
import rich
#from rich.prompt import Confirm
import pypdf
# import tiktoken
import requests
import json

from easygui import fileopenbox

STOPS = ['<|from jinja2 import Templateim_end|>']
COUNTERLIMITS = 16  #an even number
LLAMA_CPP_SERVER_URL = "http://127.0.0.1:8080"
TOKENIZE_ENDPOINT = "/tokenize"


def tokenize_text(server_url: str, text: str, add_special: bool = False, with_pieces: bool = False):
    """
    Sends text to the llama.cpp /tokenize endpoint.

    Args:
        server_url: The base URL of the llama.cpp server (e.g., "http://127.0.0.1:8080").
        text: The string content to tokenize.
        add_special: Whether to add special tokens (like BOS). Defaults to False.
        with_pieces: Whether to return token pieces along with IDs. Defaults to False.

    Returns:
        A dictionary with the tokenization result, or None if an error occurred.
    """
    endpoint = "/tokenize"
    full_url = server_url.rstrip('/') + endpoint # Ensure no double slash

    # Prepare the data payload as a Python dictionary
    payload = {
        "content": text,
        "add_special": add_special,
        "with_pieces": with_pieces
    }

    # Set the headers (requests usually does this automatically with json=...)
    headers = {
        "Content-Type": "application/json"
    }

    try:
        # Send the POST request
        # Using json=payload automatically serializes the dict to JSON
        # and sets the Content-Type header to application/json
        response = requests.post(full_url, headers=headers, json=payload)

        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        # Parse the JSON response
        res1 = response.json()
        return len(res1['tokens'])

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to or communicating with the server at {full_url}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Server responded with status {e.response.status_code}: {e.response.text}")
        return None
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response from the server.")
        print("Response text:", response.text)
        return None

def countTokens(messages):
    from jinja2 import Template
    temp2 = "{%- if tools %}\n    {{- '<|im_start|>system\\n' }}\n    {%- if messages[0].role == 'system' %}\n        {{- messages[0].content + '\\n\\n' }}\n    {%- endif %}\n    {{- \"# Tools\\n\\nYou may call one or more functions to assist with the user query.\\n\\nYou are provided with function signatures within <tools></tools> XML tags:\\n<tools>\" }}\n    {%- for tool in tools %}\n        {{- \"\\n\" }}\n        {{- tool | tojson }}\n    {%- endfor %}\n    {{- \"\\n</tools>\\n\\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\\n<tool_call>\\n{\\\"name\\\": <function-name>, \\\"arguments\\\": <args-json-object>}\\n</tool_call><|im_end|>\\n\" }}\n{%- else %}\n    {%- if messages[0].role == 'system' %}\n        {{- '<|im_start|>system\\n' + messages[0].content + '<|im_end|>\\n' }}\n    {%- endif %}\n{%- endif %}\n{%- set ns = namespace(multi_step_tool=true, last_query_index=messages|length - 1) %}\n{%- for message in messages[::-1] %}\n    {%- set index = (messages|length - 1) - loop.index0 %}\n    {%- if ns.multi_step_tool and message.role == \"user\" and not(message.content.startswith('<tool_response>') and message.content.endswith('</tool_response>')) %}\n        {%- set ns.multi_step_tool = false %}\n        {%- set ns.last_query_index = index %}\n    {%- endif %}\n{%- endfor %}\n{%- for message in messages %}\n    {%- if (message.role == \"user\") or (message.role == \"system\" and not loop.first) %}\n        {{- '<|im_start|>' + message.role + '\\n' + message.content + '<|im_end|>' + '\\n' }}\n    {%- elif message.role == \"assistant\" %}\n        {%- set content = message.content %}\n        {%- set reasoning_content = '' %}\n        {%- if message.reasoning_content is defined and message.reasoning_content is not none %}\n            {%- set reasoning_content = message.reasoning_content %}\n        {%- else %}\n            {%- if '</think>' in message.content %}\n                {%- set content = message.content.split('</think>')[-1].lstrip('\\n') %}\n                {%- set reasoning_content = message.content.split('</think>')[0].rstrip('\\n').split('<think>')[-1].lstrip('\\n') %}\n            {%- endif %}\n        {%- endif %}\n        {%- if loop.index0 > ns.last_query_index %}\n            {%- if loop.last or (not loop.last and reasoning_content) %}\n                {{- '<|im_start|>' + message.role + '\\n<think>\\n' + reasoning_content.strip('\\n') + '\\n</think>\\n\\n' + content.lstrip('\\n') }}\n            {%- else %}\n                {{- '<|im_start|>' + message.role + '\\n' + content }}\n            {%- endif %}\n        {%- else %}\n            {{- '<|im_start|>' + message.role + '\\n' + content }}\n        {%- endif %}\n        {%- if message.tool_calls %}\n            {%- for tool_call in message.tool_calls %}\n                {%- if (loop.first and content) or (not loop.first) %}\n                    {{- '\\n' }}\n                {%- endif %}\n                {%- if tool_call.function %}\n                    {%- set tool_call = tool_call.function %}\n                {%- endif %}\n                {{- '<tool_call>\\n{\"name\": \"' }}\n                {{- tool_call.name }}\n                {{- '\", \"arguments\": ' }}\n                {%- if tool_call.arguments is string %}\n                    {{- tool_call.arguments }}\n                {%- else %}\n                    {{- tool_call.arguments | tojson }}\n                {%- endif %}\n                {{- '}\\n</tool_call>' }}\n            {%- endfor %}\n        {%- endif %}\n        {{- '<|im_end|>\\n' }}\n    {%- elif message.role == \"tool\" %}\n        {%- if loop.first or (messages[loop.index0 - 1].role != \"tool\") %}\n            {{- '<|im_start|>user' }}\n        {%- endif %}\n        {{- '\\n<tool_response>\\n' }}\n        {{- message.content }}\n        {{- '\\n</tool_response>' }}\n        {%- if loop.last or (messages[loop.index0 + 1].role != \"tool\") %}\n            {{- '<|im_end|>\\n' }}\n        {%- endif %}\n    {%- endif %}\n{%- endfor %}\n{%- if add_generation_prompt %}\n    {{- '<|im_start|>assistant\\n' }}\n    {%- if enable_thinking is defined and enable_thinking is false %}\n        {{- '<think>\\n\\n</think>\\n\\n' }}\n    {%- endif %}\n{%- endif %}"
    tm = Template(temp2)
    msg=tm.render(messages=messages)
    if messages is None: return 0
    numoftokens = tokenize_text(LLAMA_CPP_SERVER_URL, msg)
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
        messages = [{"role": "user", "content": textfile}]
        num_of_tokens = countTokens(messages)
        print('Creating text file...')
        print(f"Parsed from PDF {page_count} pages of text\nA total context of {num_of_tokens} tokens ")
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
:'#######::'##:::::'##:'########:'##::: ##::'#######::
'##.... ##: ##:'##: ##: ##.....:: ###:: ##:'##.... ##:
 ##:::: ##: ##: ##: ##: ##::::::: ####: ##:..::::: ##:
 ##:::: ##: ##: ##: ##: ######::: ## ## ##::'#######::
 ##:'## ##: ##: ##: ##: ##...:::: ##. ####::...... ##:
 ##:.. ##:: ##: ##: ##: ##::::::: ##:. ###:'##:::: ##:
: ##### ##:. ###. ###:: ########: ##::. ##:. #######::
:.....:..:::...::...:::........::..::::..:::.......:::
""")
# Point to the local server
client = OpenAI(base_url="http://localhost:8080/v1", api_key="not-needed")
print("Ready to Chat with Qwen3-1.7B  Context length=16k...")
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

            buffer = ""
            is_thinking = False # State variable to track if we are inside a think block

            for chunk in completion:
                if chunk.choices[0].delta.content:
                    delta_content = chunk.choices[0].delta.content
                    buffer += delta_content

                    while True: # Process buffer for tags
                        if not is_thinking:
                            think_start_index = buffer.find("<think>")
                            if think_start_index != -1:
                                # Part before <think> tag can be printed
                                content_to_print = buffer[:think_start_index]
                                if content_to_print:
                                    print(content_to_print, end="", flush=True)
                                    new_message["content"] += content_to_print
                                
                                buffer = buffer[think_start_index:] # Keep the rest in buffer
                                is_thinking = True
                            else:
                                # No <think> tag found, print entire buffer and clear it
                                if buffer:
                                    print(buffer, end="", flush=True)
                                    new_message["content"] += buffer
                                buffer = ""
                                break # Nothing more to process in the buffer for now
                        
                        if is_thinking:
                            think_end_index = buffer.find("</think>")
                            if think_end_index != -1:
                                # Found the end of the think block
                                # The content inside the tags is in buffer[len("<think>"):think_end_index]
                                # We discard this.
                                buffer = buffer[think_end_index + len("</think>"):] # Remove the think block
                                is_thinking = False
                                # Continue loop to process the rest of the buffer
                            else:
                                # End tag not yet found in the current buffer, wait for more chunks
                                break 
                        
            # After the loop, any remaining content in the buffer (if not in a think block) should be processed/printed.
            # This can happen if the stream ends before a closing tag is found or if there's content after the last tag.
            if buffer and not is_thinking:
                print(buffer, end="", flush=True)
                new_message["content"] += buffer

            history.append(new_message)
            chathistory.append(new_message)
            print("\033[0m")
            counter += 1 
            print(f'\n📋 CHat history actual size: {countTokens(chathistory)} tokens')

        ##### RAG AND NORMaL CHAT SESSION
        else:
            if not thiking:
                userinput = lines + "/no_think \n"
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

                buffer = ""
                is_thinking = False # State variable to track if we are inside a think block

                for chunk in completion:
                    if chunk.choices[0].delta.content:
                        delta_content = chunk.choices[0].delta.content
                        buffer += delta_content

                        while True: # Process buffer for tags
                            if not is_thinking:
                                think_start_index = buffer.find("<think>")
                                if think_start_index != -1:
                                    # Part before <think> tag can be printed
                                    content_to_print = buffer[:think_start_index]
                                    if content_to_print:
                                        print(content_to_print, end="", flush=True)
                                        new_message["content"] += content_to_print
                                    
                                    buffer = buffer[think_start_index:] # Keep the rest in buffer
                                    is_thinking = True
                                else:
                                    # No <think> tag found, print entire buffer and clear it
                                    if buffer:
                                        print(buffer, end="", flush=True)
                                        new_message["content"] += buffer
                                    buffer = ""
                                    break # Nothing more to process in the buffer for now
                            
                            if is_thinking:
                                think_end_index = buffer.find("</think>")
                                if think_end_index != -1:
                                    # Found the end of the think block
                                    # The content inside the tags is in buffer[len("<think>"):think_end_index]
                                    # We discard this.
                                    buffer = buffer[think_end_index + len("</think>"):] # Remove the think block
                                    is_thinking = False
                                    # Continue loop to process the rest of the buffer
                                else:
                                    # End tag not yet found in the current buffer, wait for more chunks
                                    break 
                            
                # After the loop, any remaining content in the buffer (if not in a think block) should be processed/printed.
                # This can happen if the stream ends before a closing tag is found or if there's content after the last tag.
                if buffer and not is_thinking:
                    print(buffer, end="", flush=True)
                    new_message["content"] += buffer

                history.append(new_message)
                chathistory.append(new_message)
                print("\033[0m")
                counter += 1 
                print(f'\n📋 CHat history actual size: {countTokens(chathistory)} tokens')

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
                print("\033[0m")
                print(f'\n📋 CHat history actual size: {countTokens(chathistory)} tokens')


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

            buffer = ""
            is_thinking = False # State variable to track if we are inside a think block

            for chunk in completion:
                if chunk.choices[0].delta.content:
                    delta_content = chunk.choices[0].delta.content
                    buffer += delta_content

                    while True: # Process buffer for tags
                        if not is_thinking:
                            think_start_index = buffer.find("<think>")
                            if think_start_index != -1:
                                # Part before <think> tag can be printed
                                content_to_print = buffer[:think_start_index]
                                if content_to_print:
                                    print(content_to_print, end="", flush=True)
                                    new_message["content"] += content_to_print
                                
                                buffer = buffer[think_start_index:] # Keep the rest in buffer
                                is_thinking = True
                            else:
                                # No <think> tag found, print entire buffer and clear it
                                if buffer:
                                    print(buffer, end="", flush=True)
                                    new_message["content"] += buffer
                                buffer = ""
                                break # Nothing more to process in the buffer for now
                        
                        if is_thinking:
                            think_end_index = buffer.find("</think>")
                            if think_end_index != -1:
                                # Found the end of the think block
                                # The content inside the tags is in buffer[len("<think>"):think_end_index]
                                # We discard this.
                                buffer = buffer[think_end_index + len("</think>"):] # Remove the think block
                                is_thinking = False
                                # Continue loop to process the rest of the buffer
                            else:
                                # End tag not yet found in the current buffer, wait for more chunks
                                break 
                        
            # After the loop, any remaining content in the buffer (if not in a think block) should be processed/printed.
            # This can happen if the stream ends before a closing tag is found or if there's content after the last tag.
            if buffer and not is_thinking:
                print(buffer, end="", flush=True)
                new_message["content"] += buffer

            history.append(new_message)
            chathistory.append(new_message)
            print("\033[0m")
            counter += 1 
            print(f'\n📋 CHat history actual size: {countTokens(chathistory)} tokens')

        ##### RAG AND NORMaL CHAT SESSION
        else:
            if not thiking:
                for line in lines:
                    userinput += line + "\n"  
                userinput += "/no_think \n"
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

                buffer = ""
                is_thinking = False # State variable to track if we are inside a think block

                for chunk in completion:
                    if chunk.choices[0].delta.content:
                        delta_content = chunk.choices[0].delta.content
                        buffer += delta_content

                        while True: # Process buffer for tags
                            if not is_thinking:
                                think_start_index = buffer.find("<think>")
                                if think_start_index != -1:
                                    # Part before <think> tag can be printed
                                    content_to_print = buffer[:think_start_index]
                                    if content_to_print:
                                        print(content_to_print, end="", flush=True)
                                        new_message["content"] += content_to_print
                                    
                                    buffer = buffer[think_start_index:] # Keep the rest in buffer
                                    is_thinking = True
                                else:
                                    # No <think> tag found, print entire buffer and clear it
                                    if buffer:
                                        print(buffer, end="", flush=True)
                                        new_message["content"] += buffer
                                    buffer = ""
                                    break # Nothing more to process in the buffer for now
                            
                            if is_thinking:
                                think_end_index = buffer.find("</think>")
                                if think_end_index != -1:
                                    # Found the end of the think block
                                    # The content inside the tags is in buffer[len("<think>"):think_end_index]
                                    # We discard this.
                                    buffer = buffer[think_end_index + len("</think>"):] # Remove the think block
                                    is_thinking = False
                                    # Continue loop to process the rest of the buffer
                                else:
                                    # End tag not yet found in the current buffer, wait for more chunks
                                    break 
                            
                # After the loop, any remaining content in the buffer (if not in a think block) should be processed/printed.
                # This can happen if the stream ends before a closing tag is found or if there's content after the last tag.
                if buffer and not is_thinking:
                    print(buffer, end="", flush=True)
                    new_message["content"] += buffer

                history.append(new_message)
                chathistory.append(new_message)
                print("\033[0m")
                counter += 1 
                print(f'\n📋 CHat history actual size: {countTokens(chathistory)} tokens')

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
                print("\033[0m")
                print(f'\n📋 CHat history actual size: {countTokens(chathistory)} tokens') 
         