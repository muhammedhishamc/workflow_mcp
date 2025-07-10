# Workflow Engine MCP

A comprehensive Model Context Protocol (MCP) server for managing workflows, executions, and triggers through the Workflow Engine API. This MCP provides Claude with direct access to workflow automation capabilities.

## 📋 Available Tools (23 Total)

### **Core Workflow Management (7 tools)**
- `create_workflow` - Create workflows using YAML content or structured data
- `get_workflow` - Get detailed workflow info with execution statistics  
- `get_all_workflows` - List all workflows with formatted output
- `update_workflow` - Update workflow metadata (name, description, version)
- `delete_workflow` - Delete workflows ⚠️ (permanent)
- `get_workflow_dashboard` - Get comprehensive analytics dashboard
- `validate_workflow_yaml` - Validate YAML before creation

### **Workflow Execution (2 tools)**
- `execute_workflow` - Execute workflows with custom inputs
- `get_workflow_input_format` - Get workflow input schemas/requirements

### **Execution Monitoring (5 tools)**
- `get_execution_status` - Get execution status with task breakdown
- `get_all_executions` - List all executions with status indicators
- `get_execution_logs` - Get real-time execution logs
- `get_task_output` - Get detailed task-specific output
- `get_workflow_execution_logs` - Get paginated workflow execution history

### **Trigger Management (7 tools)**
- `create_trigger` - Create automation triggers (scheduled, manual, webhook)
- `get_all_triggers` - List all triggers with status
- `get_trigger` - Get specific trigger details
- `get_workflow_triggers` - Get triggers for specific workflow
- `update_trigger` - Update trigger settings (schedule, enabled/disabled)
- `delete_trigger` - Delete triggers ⚠️ (permanent)  
- `execute_trigger` - Manually execute triggers with custom inputs

### **System & Monitoring (2 tools)**
- `get_workers_status` - Get worker system status
- `wait_for_execution_completion` - Wait for execution with real-time monitoring

## 🔌 Adding to Claude Desktop

1. **Edit Claude Desktop config** (`~/.config/claude-desktop/mcp_settings.json` on Linux/Mac or `%APPDATA%\Claude\mcp_settings.json` on Windows):

```json
{
  "mcpServers": {
    "workflow-engine": {
      "command": "uvx",
      "args": ["git+https://github.com/muhammedhishamc/workflow_mcp.git"],
      "env": {
        "WORKFLOW_BASE_URL": "https://your-workflow-engine.com"
      }
    }
  }
}
```

2. **Restart Claude Desktop** - The MCP will be available immediately

## 🖥️ Adding to Claude Code

```
claude mcp add workflow-engine -e WORKFLOW_BASE_URL=https://your-workflow-engine.com -- uvx git+https://github.com/muhammedhishamc/workflow_mcp.git
```