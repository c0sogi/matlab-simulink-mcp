# MATLAB Simulink MCP

An MCP server that allows Large Language Models (LLMs) to interact with **MATLAB** and **Simulink**,
including executing commands and working with Simulink models.

This project is forked from  
[jefferson-research/matlab-simulink-mcp](https://github.com/jefferson-research/matlab-simulink-mcp)


## ✨ Features
- Execute MATLAB commands via MCP
- Load, modify, and simulate Simulink models
- Query model structure (blocks, parameters, connections)
- Automate analysis and visualization workflows


## 🚀 Usage

### Option 1: Using Cursor IDE (Recommended)

If you are using **Cursor**, you can easily import this MCP server using the provided configuration file.
This enables Cursor agents to call MATLAB and Simulink directly via MCP.

➡️ Use the [`mcp.json`](.cursor/mcp.json) file to register the MCP server in Cursor.


### Option 2: Run the MCP Server Manually (STDIO)

Clone the repository:

```bash
git clone https://github.com/c0sogi/matlab-simulink-mcp.git
```

Change working directory:
```
cd matlab-simulink-mcp
```

Start the server:

```bash
uv run matlab-simulink-mcp
```


## 📌 Notes

- MATLAB must be installed and accessible from your system PATH.
- The MCP server communicates via **STDIO**.
- Tested primarily with Cursor, but should work with other MCP clients.

---

## 📄 License

This project follows the same license as the original repository:  
[jefferson-research/matlab-simulink-mcp](https://github.com/jefferson-research/matlab-simulink-mcp)
