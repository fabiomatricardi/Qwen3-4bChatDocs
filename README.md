# Qwen3-4bChatDocs
Textual interface to chat with your documents using llama-cpp server and Qwen3-4b.gguf

Tested on Windows 11 PC, running Python 3.12.5

### Instructions
- Clone the repo
- create a `venv` and activate it
```
python -m venv venv
.\venv\Scripts\activate
```
- Install the dependencies
```
pip install easygui tiktoken pypdf rich openai
```
- download the file Qwen_Qwen3-4B-Q4_K_L.gguf from the Bartowski repository [HuggingFaceHub](https://huggingface.co/bartowski/Qwen_Qwen3-4B-GGUF/resolve/main/Qwen_Qwen3-4B-Q4_K_L.gguf?download=true) or [HF-Mirror](https://hf-mirror.com/bartowski/Qwen_Qwen3-4B-GGUF/resolve/main/Qwen_Qwen3-4B-Q4_K_L.gguf?download=true)
- The llama-server files are already included in the Repo, with the Vulkan driver flavour.
- Open a new terminal in the Project repo 
- Run the llamaserver, where `-c` is the context window
```
.\llama-server.exe -m .\Qwen_Qwen3-4B-Q4_K_L.gguf -c 32768
```
if you have a GPU you can also offload some layers with the `-ngl` flag
The command below will offload all Layers
```
.\llama-server.exe -m .\Qwen_Qwen3-4B-Q4_K_L.gguf -c 32768 -ngl 37
```
- In another terminal window, with the `venv` activated, run
```
python .\QWEN3-4B-it.py
```


### Interface commands
```
/clear      clear the chat history and reset flags, including RAG
/multi      multi line input Enter your text (end input with Ctrl+D on Unix or Ctrl+Z on Windows)
/help       display help message and commands
/rag        load a pdf from your pc and start RAG session
/exit       end program
/think      activate thinking mode
/no_think   deactivate thinking mode
```

> NOTE: Remember that Starting multi line input, you need to  Enter your text (end input with Ctrl+D on Unix or Ctrl+Z on Windows)



