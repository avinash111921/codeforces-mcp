# Codeforces MCP Server

A Model Context Protocol (MCP) server for Codeforces competitive programming. This server enables AI coding assistants (like Claude, Cursor, and Cline) to autonomously fetch problem statements, analyze your submission history, recommend upsolving targets, and run automated local stress tests.

## Features

- **Profile & Stats**: Fetch live user ratings, ranks, and recent verdict breakdowns.
- **Problem Scraping**: Bypasses Cloudflare to extract full problem descriptions and exact sample test cases.
- **Local Sandbox**: Compiles and executes C++ or Python solutions locally against official sample inputs.
- **Automated Stress Testing**: Isolates minimal failing test cases by running your optimized code against a brute-force script and a random generator.
- **Rate-Limit Safe**: Built-in queuing and caching ensures you never hit the Codeforces API 1-request-per-2-seconds limit.

## Installation & Usage

You can run this server seamlessly using `uvx` without manual installation. Add the following configuration to your preferred AI IDE.

### Cursor
Add this to your MCP configuration (`Settings > Features > MCP`):
```json
{
  "mcpServers": {
    "codeforces-mcp": {
      "command": "uvx",
      "args": ["codeforces-mcp"]
    }
  }
}