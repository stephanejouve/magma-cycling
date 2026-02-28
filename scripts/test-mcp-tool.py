#!/usr/bin/env python3
"""
MCP Tool Tester - Test MCP tools without Claude Desktop.

Usage:
    # Test list-weeks
    poetry run python scripts/test-mcp-tool.py list-weeks

    # Test get-week-details
    poetry run python scripts/test-mcp-tool.py get-week-details '{"week_id": "S081"}'

    # Test update-session
    poetry run python scripts/test-mcp-tool.py update-session '{"week_id": "S081", "session_id": "S081-01", "status": "completed"}'

Benefits:
- Test MCP tools instantly without restarting Claude Desktop
- See raw JSON responses
- Fast iteration during development
- Debug tool issues
"""

import asyncio
import json
import sys


async def test_tool(tool_name: str, arguments: dict):
    """Test a specific MCP tool."""
    from magma_cycling.mcp_server import call_tool

    print(f"🧪 Testing tool: {tool_name}")
    print(f"   Arguments: {json.dumps(arguments, indent=2)}\n")

    try:
        result = await call_tool(tool_name, arguments)

        print("✅ Result:")
        for content in result:
            print(content.text)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Parse command line arguments and run test."""
    if len(sys.argv) < 2:
        print("Usage: poetry run python scripts/test-mcp-tool.py <tool-name> [args-json]")
        print("\nAvailable tools:")
        print("  - weekly-planner")
        print("  - monthly-analysis")
        print("  - daily-sync")
        print("  - update-session")
        print("  - list-weeks")
        print("  - get-metrics")
        print("  - get-week-details")
        print("\nExamples:")
        print("  poetry run python scripts/test-mcp-tool.py list-weeks")
        print(
            '  poetry run python scripts/test-mcp-tool.py get-week-details \'{"week_id": "S081"}\''
        )
        sys.exit(1)

    tool_name = sys.argv[1]
    arguments = {}

    if len(sys.argv) >= 3:
        try:
            arguments = json.loads(sys.argv[2])
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON arguments: {e}")
            sys.exit(1)

    asyncio.run(test_tool(tool_name, arguments))


if __name__ == "__main__":
    main()
