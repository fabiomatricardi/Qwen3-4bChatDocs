# Qwen3-4bChatDocs
Textual interface to chat with your documents using llama-cpp server and Qwen3-4b.gguf

Tested on Windows 11 PC, running Python 3.12.5

### Instructions
> **⚠️You need to have GIT installed on your PC**
- Clone the repo
```
git clone https://github.com/fabiomatricardi/Qwen3-4bChatDocs.git
```
- Enter the Project directory
`cd Qwen3-4bChatDocs`

From the terminal run `install.bat` that will automatically:
- create and activate a `venv`
- install the dependencies
- download the GGUF file
- unzip the llama.cpp binaries
- run the server
- start the python chat application


#### If you want to do it manually...
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
- The llama-server files are already included in the ZIP archive `llama-b5273-bin-win-vulkan-x64.zip` from this Repo, with the Vulkan driver flavour.
Unzip the archive in your Project repo directory (if you cloned this Repo `Qwen3-4bChatDocs`
- Open a new terminal in the Project repo directory
- Run the llamaserver, where `-c` is the context window
```
.\llama-server.exe -m .\Qwen_Qwen3-4B-Q4_K_L.gguf -c 16348
```
> Note that this model has a 32k context capability, but the VRAM requirements are really high. So I started setting it into half 

If you have a GPU you can also offload some layers with the `-ngl` flag
The command below will offload all Layers
If you don't know use `-ngl 999`
```
.\llama-server.exe -m .\Qwen_Qwen3-4B-Q4_K_L.gguf -c 16348 -ngl 37
```
- In another terminal window, with the `venv` activated, run
```
python .\QWEN3-4B-it.py
```

Or after the intallation and download process, run from the terminal, with the venv activated:
```
start.bat
```

### VRAM and RAM requirements
The Qwen3-4B Language Model has 37 layers.
The version we donwloaded is the **Q4_K_L** that uses Uses Q8_0 for embed and output weights.
So, to sum it up, you need only 2.5 Gb to run the model... BUT the KV cache used for the context lenght can be even higher!

For example, if you set `-c 16348` (16k tokens context window) you need quite a lot of VRAM/RAM
```
llama_kv_cache_unified: kv_size = 16352, type_k = 'f16', type_v = 'f16', n_layer = 36, can_shift = 1, padding = 32
llama_kv_cache_unified:        CPU KV buffer size =  2299.50 MiB
llama_kv_cache_unified: KV self size  = 2299.50 MiB, K (f16): 1149.75 MiB, V (f16): 1149.75 MiB
llama_context:    Vulkan0 compute buffer size =  1181.38 MiB
llama_context: Vulkan_Host compute buffer size =    36.94 MiB
```
```
weights:    2.5 Gb
KV cache:   2.3 Gb
Compute:    1.2 Gb
------------------
Total       6.0 Gb
```

What does it mean?
- modify the start.bat file starting with little context (8192), or less layers offloaded to GPU (if you have any)
- increase little by little
- be ready to wait many seconds before the first token is generated

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


### Limitations
This is a Naive implementation of RAG, not relying of any kind of embedding strategy
It is more an ICL (In Context Learning) application, where the model Read and retrieve through the prompt, following the user instructions.
#### Missing part
For now there is no check on the lenght of the document, and there is no control on the number of tokens in the chat history. It is turn based (max turns is 16, after that the chat history is trimmed keeping the last 14 turns)


### External software and attribution
- [Windows binaries of GNU Wget](https://eternallybored.org/misc/wget/) 









