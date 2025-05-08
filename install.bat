echo off
echo Downloading the Language model...
wget https://hf-mirror.com/bartowski/Qwen_Qwen3-4B-GGUF/resolve/main/Qwen_Qwen3-4B-Q4_K_L.gguf -nv --show-progress
echo Unzipping the llama.cpp binaries...
tar -xf llama-b5273-bin-win-vulkan-x64.zip
echo Creating Virtual environment
python -m venv venv
echo Activating venv
call .\venv\Scripts\activate.bat
echo Installing dependencies
pip install easygui tiktoken pypdf rich openai requests jinja2
start cmd.exe /c llama-server.exe -m Qwen_Qwen3-4B-Q4_K_L.gguf -c 16348 -ngl 999
python QWEN3-4B-it.py
PAUSE
