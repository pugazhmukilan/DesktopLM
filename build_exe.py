"""
Build DesktopLM into a standalone executable using PyInstaller.

Usage:
    python build_exe.py

Output:
    dist/desktoplm/desktoplm.exe
"""

import subprocess
import sys
import os

def build():
    print("=" * 50)
    print("  DesktopLM v0.2.0 -- PyInstaller Build")
    print("=" * 50)
    
    # Collect data files that must ship with the exe
    sep = os.pathsep  # ";" on Windows
    
    args = [
        sys.executable,
        "-m", "PyInstaller",
        "--name", "desktoplm",
        "--onedir",
        "--noconfirm",
        "--clean",
        "--console",
        
        # ---- Data files that must be bundled ----
        f"--add-data=tools/mcp_config.json{sep}tools",
        f"--add-data=LLMS/sys_prompt_slm.py{sep}LLMS",
        f"--add-data=.env{sep}.",
        
        # ---- Hidden imports (dynamic imports PyInstaller can't detect) ----
        # LangChain ecosystem
        "--hidden-import=langchain",
        "--hidden-import=langchain_core",
        "--hidden-import=langchain_core.tools",
        "--hidden-import=langchain_core.messages",
        "--hidden-import=langchain_core.callbacks",
        "--hidden-import=langchain_core.prompts",
        "--hidden-import=langchain_core.output_parsers",
        "--hidden-import=langchain_ollama",
        "--hidden-import=langchain_google_genai",
        "--hidden-import=langchain_openai",
        "--hidden-import=langgraph",
        "--hidden-import=langgraph.prebuilt",
        
        # Pydantic (used heavily by LangChain)
        "--hidden-import=pydantic",
        "--hidden-import=pydantic.deprecated",
        "--hidden-import=pydantic.deprecated.decorator",
        
        # ChromaDB + ONNX (vector memory)
        "--hidden-import=chromadb",
        "--hidden-import=chromadb.config",
        "--hidden-import=chromadb.api",
        "--hidden-import=chromadb.api.segment",
        "--hidden-import=chromadb.telemetry.product.posthog",
        "--hidden-import=onnxruntime",
        "--hidden-import=tokenizers",
        "--hidden-import=hnswlib",
        
        # SQLAlchemy (SQL memory)
        "--hidden-import=sqlalchemy",
        "--hidden-import=sqlalchemy.dialects.sqlite",
        
        # MongoDB (NoSQL memory)
        "--hidden-import=pymongo",
        
        # Web search
        "--hidden-import=ddgs",
        "--hidden-import=bs4",
        "--hidden-import=requests",
        
        # Dotenv
        "--hidden-import=dotenv",
        
        # Ollama
        "--hidden-import=ollama",
        
        # Google GenAI
        "--hidden-import=google.generativeai",
        
        # Standard lib that PyInstaller sometimes misses
        "--hidden-import=uuid",
        "--hidden-import=concurrent.futures",
        
        # Our own packages (ensure they are collected)
        "--collect-submodules=agent",
        "--collect-submodules=LLMS",
        "--collect-submodules=MemoryManager",
        "--collect-submodules=tools",
        "--collect-submodules=chromadb",
        "--collect-submodules=langchain_core",
        "--collect-submodules=langchain_ollama",
        "--collect-submodules=langgraph",
        
        # Collect all data for packages that need runtime data files
        "--collect-data=chromadb",
        "--collect-data=langchain",
        "--collect-data=langchain_core",
        "--collect-data=pydantic",
        "--collect-data=tokenizers",
        "--collect-data=certifi",
        
        # Entry point
        "main.py",
    ]
    
    print(f"\nRunning PyInstaller with {len(args)} arguments...")
    print("This may take 3-10 minutes depending on your machine.\n")
    
    result = subprocess.run(args, cwd=os.path.dirname(os.path.abspath(__file__)))
    
    if result.returncode == 0:
        print("\n" + "=" * 50)
        print("  BUILD SUCCESSFUL!")
        print("  Output: dist/desktoplm/desktoplm.exe")
        print("=" * 50)
        print("\nTo share with friends:")
        print("  1. Zip the entire 'dist/desktoplm/' folder")
        print("  2. Your friend unzips it anywhere on their PC")
        print("  3. They create a .env file with their Ollama/API config")
        print("  4. They run: desktoplm.exe repl")
    else:
        print(f"\nBuild FAILED with exit code {result.returncode}")
        
    return result.returncode

if __name__ == "__main__":
    raise SystemExit(build())
