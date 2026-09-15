#!/bin/bash
cd ~/llm_project/third_party/llama.cpp
export LD_LIBRARY_PATH=~/llm_project/third_party/llama.cpp/build/bin:$LD_LIBRARY_PATH
./build/bin/llama-server \
    -m ~/llm_project/models/Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf \
    --port 8080 \
    -c 8192
