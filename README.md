# LaTeX MCP Server

A Model Context Protocol server for compiling LaTeX documents.

## Features

- LaTeX compilation
- PDF generation
- Tectonic engine
- MCP integration
- Timeout protection
- File size limits

## Installation

Clone:

git clone https://github.com/volkanmydn/latex-mcp-server.git

Install dependencies:

pip install -r requirements.txt

## Run

python src/main.py

## Tools

### compile_latex

Compiles LaTeX source code and returns PDF.

### get_policy_info

Shows server security limits.

## Security

Default:

- Network: disabled
- Shell escape: disabled
- Timeout enabled
- Source size limit enabled