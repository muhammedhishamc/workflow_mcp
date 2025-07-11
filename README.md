# Workflow Engine MCP Server

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

## 🚀 Installation & Setup

### Prerequisites
- Python 3.12+
- Workflow Engine API access
- Environment variables configured

### Environment Variables
Create a `.env` file in the project root:

```bash
WORKFLOW_BASE_URL="https://your-workflow-engine.com"
```

### Local Development
```bash
# Clone the repository
git clone https://github.com/muhammedhishamc/workflow_mcp.git
cd workflow_mcp

# Install dependencies
pip install -e .

# Run the server
python main.py
```

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

```bash
claude mcp add workflow-engine -e WORKFLOW_BASE_URL=https://your-workflow-engine.com -- uvx git+https://github.com/muhammedhishamc/workflow_mcp.git
```

## 🏗️ Architecture

### Core Components

1. **WorkflowClient** - HTTP client for Workflow Engine API
   - Handles authentication and API communication
   - Implements retry logic and error handling
   - Provides response formatting

2. **MCP Server** - Model Context Protocol server
   - Defines 23 tools across 5 categories
   - Handles tool execution and response formatting
   - Manages server lifecycle and initialization

3. **Error Handling** - Comprehensive error management
   - Custom exception classes
   - Retry mechanisms with exponential backoff
   - Graceful error reporting

### Request Flow

```
Claude → MCP Server → WorkflowClient → Workflow Engine API
                ↓
      Formatted Response ← HTTP Response ← API Response
```

## 🛠️ API Coverage

The MCP server provides complete coverage of the Workflow Engine API:

- **Workflows**: Full CRUD operations with validation
- **Executions**: Real-time monitoring and log retrieval
- **Triggers**: Automated scheduling and manual execution
- **System**: Worker status and health monitoring
- **Analytics**: Dashboard metrics and execution statistics

## 🔧 Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `WORKFLOW_BASE_URL` | Base URL of the Workflow Engine API | `https://workflow-api.example.com` |

### Optional Configuration

- **Timeout**: HTTP request timeout (default: 30 seconds)
- **Retry**: Maximum retry attempts (default: 3)
- **Polling**: Execution polling interval (default: 5 seconds)

## 📊 Features

### Rich Response Formatting
- Emoji indicators for status and types
- Structured output with headers and sections
- Raw JSON data for complete information
- Progress tracking for long-running operations

### Error Handling
- Comprehensive error reporting
- API error details and HTTP status codes
- Retry mechanisms for transient failures
- Graceful degradation for partial failures

### Real-time Monitoring
- Live execution status tracking
- Real-time log streaming
- Progress indicators and completion notifications
- Timeout handling with status updates

## 🧪 Testing

```bash
# Run basic connectivity test
python -c "from main import initialize_client; initialize_client(); print('Client initialized successfully')"

# Test specific tool (example)
python -c "
import asyncio
from main import workflow_client, initialize_client
initialize_client()
result = asyncio.run(workflow_client.get_all_workflows())
print(result)
"
```

## 🔒 Security

- Environment variable-based configuration
- HTTPS-only API communication
- No hardcoded credentials or URLs
- Secure error handling (no sensitive data exposure)

## 📈 Performance

- Asynchronous HTTP requests with httpx
- Connection pooling and reuse
- Efficient response formatting
- Minimal memory footprint

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
- GitHub Issues: [workflow_mcp/issues](https://github.com/muhammedhishamc/workflow_mcp/issues)
- Documentation: See README.md and code comments
- API Documentation: Check the Workflow Engine API docs

---

**Note**: This MCP server requires a running Workflow Engine API instance. Make sure your `WORKFLOW_BASE_URL` points to a valid and accessible API endpoint.
