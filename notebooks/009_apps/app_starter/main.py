from mcp.server.fastmcp import FastMCP
from tools.document import document_path_to_markdown
from tools.math import add

mcp = FastMCP("docs")

mcp.tool()(add)
mcp.tool()(document_path_to_markdown)

if __name__ == "__main__":
    mcp.run()
