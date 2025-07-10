"""
Workflow Engine MCP Server - A Model Context Protocol server for Workflow Engine API operations

This server provides complete integration with the Workflow Engine API,
including workflow management, execution monitoring, trigger management,
and comprehensive analytics capabilities.
"""

import asyncio
import json
import logging
import sys
import time
from typing import Dict, Optional, Any
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
import httpx
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

class WorkflowAPIError(Exception):
    """Custom exception for Workflow API errors"""
    pass

class WorkflowAuthError(Exception):
    """Custom exception for Workflow authentication errors"""
    pass

class WorkflowClient:
    """Workflow Engine API client for MCP server"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.environ.get("WORKFLOW_BASE_URL")
        if not self.base_url:
            raise WorkflowAuthError("WORKFLOW_BASE_URL environment variable must be set")
        
        self.api_base_url = f"{self.base_url}/api"
        self.headers = {"Content-Type": "application/json"}
    
    async def _make_request(self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None,
                        headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP request to Workflow Engine API with proper error handling"""
        url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        json=payload,
                        headers=request_headers,
                        params=params,
                        timeout=30.0
                    )
                    
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', 1))
                        await asyncio.sleep(retry_after)
                        retry_count += 1
                        continue
                    
                    # Check if the response is successful
                    if response.status_code >= 400:
                        error_detail = ""
                        try:
                            error_data = response.json()
                            error_detail = json.dumps(error_data, indent=2)
                        except:
                            error_detail = response.text
                        
                        raise WorkflowAPIError(f"HTTP {response.status_code}: {error_detail}")
                    
                    # Try to parse JSON response
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        # If response is not JSON, return the text content
                        return {"message": response.text, "status_code": response.status_code}
                        
            except httpx.TimeoutException:
                if retry_count == max_retries - 1:
                    raise WorkflowAPIError("Request timed out after maximum retries")
                retry_count += 1
                await asyncio.sleep(1)
            except httpx.RequestError as e:
                if retry_count == max_retries - 1:
                    raise WorkflowAPIError(f"Request failed: {str(e)}")
                retry_count += 1
                await asyncio.sleep(1)
    
    def _format_response(self, data: Dict[str, Any], title: str) -> str:
        """Format response data for better readability"""
        formatted = f"=== {title} ===\n"
        
        if isinstance(data, dict):
            # Handle execution statistics if present
            if "execution_statistics" in data:
                stats = data["execution_statistics"]
                formatted += f"📊 **Execution Statistics:**\n"
                formatted += f"   • Total Executions: {stats.get('total_executions', 0)}\n"
                formatted += f"   • Success Rate: {stats.get('success_rate', 0)}%\n"
                formatted += f"   • Failure Rate: {stats.get('failure_rate', 0)}%\n"
                formatted += f"   • Average Duration: {stats.get('avg_duration_seconds', 0)} seconds\n"
                formatted += f"   • Total Runtime: {stats.get('total_runtime_hours', 0)} hours\n"
                formatted += f"   • First Execution: {stats.get('first_execution_at', 'N/A')}\n"
                formatted += f"   • Last Execution: {stats.get('last_execution_at', 'N/A')}\n\n"
            
            # Handle dashboard metrics if present
            if "metrics" in data:
                metrics = data["metrics"]
                formatted += f"📈 **Dashboard Metrics:**\n"
                
                if "success_ratio" in metrics:
                    success = metrics["success_ratio"]
                    formatted += f"   • Success: {success.get('count', 0)}/{success.get('total', 0)} ({success.get('percentage', 0)}%)\n"
                
                if "duration_stats" in metrics:
                    duration = metrics["duration_stats"]
                    formatted += f"   • Duration Stats:\n"
                    formatted += f"     - Average: {duration.get('avg_duration_seconds', 0)} seconds\n"
                    formatted += f"     - Min/Max: {duration.get('min_duration_seconds', 0)}/{duration.get('max_duration_seconds', 0)} seconds\n"
                    formatted += f"     - Total Runtime: {duration.get('total_runtime_hours', 0)} hours\n"
                
                formatted += "\n"
            
            # Handle logs with better formatting
            if "logs" in data and isinstance(data["logs"], list):
                formatted += f"📋 **Logs ({data.get('total_logs', len(data['logs']))} total):**\n"
                for log in data["logs"][-10:]:  # Show last 10 logs
                    level = log.get('level', 'INFO')
                    task_id = log.get('task_id', 'unknown')
                    message = log.get('message', 'No message')
                    formatted += f"   [{level}] {task_id}: {message}\n"
                formatted += "\n"
            
            # Handle trigger information
            if "triggers" in data and isinstance(data["triggers"], list):
                formatted += f"🔗 **Triggers ({len(data['triggers'])} total):**\n"
                for trigger in data["triggers"]:
                    name = trigger.get('name', 'Unnamed')
                    trigger_type = trigger.get('trigger_type', 'unknown')
                    enabled = "🟢 Enabled" if trigger.get('enabled') else "🔴 Disabled"
                    formatted += f"   • {name} ({trigger_type}): {enabled}\n"
                formatted += "\n"
        
        # Add raw JSON for complete data
        formatted += f"**Raw Data:**\n```json\n{json.dumps(data, indent=2)}\n```"
        
        return formatted
    
    # ============ CORE WORKFLOW MANAGEMENT ============
    
    async def create_workflow(self, yaml_content: Optional[str] = None, 
                            workflow_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new workflow using YAML content or workflow data"""
        if not yaml_content and not workflow_data:
            raise ValueError("Either yaml_content or workflow_data is required")
        
        payload = {}
        if yaml_content:
            payload["yaml_content"] = yaml_content
        elif workflow_data:
            payload["workflow_data"] = workflow_data
        
        return await self._make_request("POST", "workflows", payload)
    
    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get detailed workflow information with execution statistics"""
        return await self._make_request("GET", f"workflows/{workflow_id}")
    
    async def get_all_workflows(self) -> Dict[str, Any]:
        """Get all workflows"""
        return await self._make_request("GET", "workflows")
    
    async def update_workflow(self, workflow_id: str, name: Optional[str] = None,
                            description: Optional[str] = None, version: Optional[str] = None,
                            **kwargs) -> Dict[str, Any]:
        """Update an existing workflow's metadata"""
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if version is not None:
            payload["version"] = version
        
        payload.update(kwargs)
        return await self._make_request("PUT", f"workflows/{workflow_id}", payload)
    
    async def delete_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Delete a workflow by ID"""
        return await self._make_request("DELETE", f"workflows/{workflow_id}")
    
    async def get_workflow_dashboard(self, workflow_id: str) -> Dict[str, Any]:
        """Get comprehensive workflow dashboard with metrics and analytics"""
        return await self._make_request("GET", f"workflows/{workflow_id}/dashboard")
    
    async def validate_workflow_yaml(self, yaml_content: str) -> Dict[str, Any]:
        """Validate YAML workflow content before creation"""
        payload = {"yaml_content": yaml_content}
        return await self._make_request("POST", "validate", payload)
    
    # ============ WORKFLOW EXECUTION ============
    
    async def execute_workflow(self, workflow_id: str, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a workflow with provided inputs"""
        payload = {"inputs": inputs or {}}
        return await self._make_request("POST", f"workflows/{workflow_id}/execute", payload)
    
    async def get_workflow_input_format(self, workflow_id: str) -> Dict[str, Any]:
        """Get the input format/schema for a specific workflow"""
        return await self._make_request("GET", f"workflows/{workflow_id}")
    
    # ============ EXECUTION MONITORING ============
    
    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get the status and details of a workflow execution"""
        return await self._make_request("GET", f"executions/{execution_id}")
    
    async def get_all_executions(self) -> Dict[str, Any]:
        """Get all workflow executions"""
        return await self._make_request("GET", "executions")
    
    async def get_execution_logs(self, execution_id: str) -> Dict[str, Any]:
        """Get real-time execution logs"""
        return await self._make_request("GET", f"executions/{execution_id}/logs")
    
    async def get_task_output(self, execution_id: str, task_id: str) -> Dict[str, Any]:
        """Get detailed output for a specific task within an execution"""
        return await self._make_request("GET", f"executions/{execution_id}/tasks/{task_id}")
    
    async def get_workflow_execution_logs(self, workflow_id: str, page: int = 1, per_page: int = 10,
                                        status: Optional[str] = None, include_logs: bool = True) -> Dict[str, Any]:
        """Get paginated execution logs for a specific workflow"""
        params = {
            "page": page,
            "per_page": per_page,
            "include_logs": str(include_logs).lower()
        }
        if status:
            params["status"] = status
        
        return await self._make_request("GET", f"workflows/{workflow_id}/executions/logs", params=params)
    
    # ============ TRIGGER MANAGEMENT ============
    
    async def create_trigger(self, name: str, workflow_id: str, trigger_type: str,
                        schedule: Optional[str] = None, enabled: bool = True,
                        description: Optional[str] = None, config: Optional[Dict[str, Any]] = None,
                           input_mapping: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Create a new trigger for workflow automation"""
        payload = {
            "name": name,
            "workflow_id": workflow_id,
            "trigger_type": trigger_type,
            "enabled": enabled
        }
        
        if schedule is not None:
            payload["schedule"] = schedule
        if description is not None:
            payload["description"] = description
        if config is not None:
            payload["config"] = config
        if input_mapping is not None:
            payload["input_mapping"] = input_mapping
        
        payload.update(kwargs)
        return await self._make_request("POST", "triggers", payload)
    
    async def get_all_triggers(self) -> Dict[str, Any]:
        """Get all triggers"""
        return await self._make_request("GET", "triggers")
    
    async def get_trigger(self, trigger_id: str) -> Dict[str, Any]:
        """Get specific trigger details"""
        return await self._make_request("GET", f"triggers/{trigger_id}")
    
    async def get_workflow_triggers(self, workflow_id: str) -> Dict[str, Any]:
        """Get all triggers for a specific workflow"""
        return await self._make_request("GET", f"workflows/{workflow_id}/triggers")
    
    async def update_trigger(self, trigger_id: str, name: Optional[str] = None,
                        schedule: Optional[str] = None, enabled: Optional[bool] = None,
                           description: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Update an existing trigger"""
        payload = {}
        if name is not None:
            payload["name"] = name
        if schedule is not None:
            payload["schedule"] = schedule
        if enabled is not None:
            payload["enabled"] = enabled
        if description is not None:
            payload["description"] = description
        
        payload.update(kwargs)
        return await self._make_request("PUT", f"triggers/{trigger_id}", payload)
    
    async def delete_trigger(self, trigger_id: str) -> Dict[str, Any]:
        """Delete a trigger by ID"""
        return await self._make_request("DELETE", f"triggers/{trigger_id}")
    
    async def execute_trigger(self, trigger_id: str, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Manually execute a trigger with custom inputs"""
        payload = {"inputs": inputs or {}}
        return await self._make_request("POST", f"triggers/{trigger_id}/execute", payload)
    
    # ============ SYSTEM AND MONITORING ============
    
    async def get_workers_status(self) -> Dict[str, Any]:
        """Get the status of all workflow workers"""
        return await self._make_request("GET", "workers/status")
    
    async def wait_for_execution_completion(self, execution_id: str, poll_interval: int = 5,
                                        timeout: int = 300, show_logs: bool = False) -> Dict[str, Any]:
        """Wait for a workflow execution to complete with polling"""
        start_time = asyncio.get_event_loop().time()
        last_log_count = 0
        status_updates = []
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            # Get execution status
            status_result = await self.get_execution_status(execution_id)
            current_status = status_result.get("status", "Unknown")
            elapsed_time = asyncio.get_event_loop().time() - start_time
            status_updates.append(f"[{elapsed_time:.1f}s] Status: {current_status}")
            
            # Show real-time logs if requested
            if show_logs:
                try:
                    logs_result = await self.get_execution_logs(execution_id)
                    logs = logs_result.get('logs', [])
                    new_logs = logs[last_log_count:]
                    
                    for log in new_logs:
                        level = log.get('level', 'INFO')
                        task_id = log.get('task_id', 'unknown')
                        message = log.get('message', 'No message')
                        status_updates.append(f"    [{level}] {task_id}: {message}")
                    
                    last_log_count = len(logs)
                except:
                    pass  # Continue without logs if they fail
            
            # Check if execution is complete
            if current_status in ['COMPLETED', 'FAILED']:
                return {
                    "status": "finished",
                    "final_status": current_status,
                    "elapsed_time": elapsed_time,
                    "status_updates": status_updates,
                    "final_result": status_result
                }
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
        
        # Timeout reached
        return {
            "status": "timeout",
            "elapsed_time": timeout,
            "status_updates": status_updates,
            "message": f"Execution did not complete within {timeout} seconds"
        }

# Initialize the MCP server
server = Server("workflow-engine-mcp-server")

# Global client instance
workflow_client: Optional[WorkflowClient] = None

def initialize_client():
    """Initialize the Workflow client"""
    global workflow_client
    try:
        workflow_client = WorkflowClient(
            base_url=os.environ.get("WORKFLOW_BASE_URL")
        )
    except Exception as e:
        logging.error(f"Failed to initialize Workflow client: {e}")
        raise

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Workflow tools"""
    return [
        # Core Workflow Management
        types.Tool(
            name="create_workflow",
            description="Create workflows using YAML content or structured data",
            inputSchema={
                "type": "object",
                "properties": {
                    "yaml_content": {"type": "string", "description": "YAML content for the workflow"},
                    "workflow_data": {"type": "object", "description": "Structured workflow data"}
                }
            }
        ),
        types.Tool(
            name="get_workflow",
            description="Get detailed workflow info with execution statistics",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "The workflow ID"}
                },
                "required": ["workflow_id"]
            }
        ),
        types.Tool(
            name="get_all_workflows",
            description="List all workflows with formatted output",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="update_workflow",
            description="Update workflow metadata (name, description, version)",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "The workflow ID"},
                    "name": {"type": "string", "description": "New workflow name"},
                    "description": {"type": "string", "description": "New workflow description"},
                    "version": {"type": "string", "description": "New workflow version"}
                },
                "required": ["workflow_id"]
            }
        ),
        types.Tool(
            name="delete_workflow",
            description="Delete workflows (permanent)",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "The workflow ID"}
                },
                "required": ["workflow_id"]
            }
        ),
        types.Tool(
            name="get_workflow_dashboard",
            description="Get comprehensive analytics dashboard",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "The workflow ID"}
                },
                "required": ["workflow_id"]
            }
        ),
        types.Tool(
            name="validate_workflow_yaml",
            description="Validate YAML before creation",
            inputSchema={
                "type": "object",
                "properties": {
                    "yaml_content": {"type": "string", "description": "YAML content to validate"}
                },
                "required": ["yaml_content"]
            }
        ),
        
        # Workflow Execution
        types.Tool(
            name="execute_workflow",
            description="Execute workflows with custom inputs",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "The workflow ID"},
                    "inputs": {"type": "object", "description": "Input data for the workflow"}
                },
                "required": ["workflow_id"]
            }
        ),
        types.Tool(
            name="get_workflow_input_format",
            description="Get workflow input schemas/requirements",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "The workflow ID"}
                },
                "required": ["workflow_id"]
            }
        ),
        
        # Execution Monitoring
        types.Tool(
            name="get_execution_status",
            description="Get execution status with task breakdown",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {"type": "string", "description": "The execution ID"}
                },
                "required": ["execution_id"]
            }
        ),
        types.Tool(
            name="get_all_executions",
            description="List all executions with status indicators",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="get_execution_logs",
            description="Get real-time execution logs",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {"type": "string", "description": "The execution ID"}
                },
                "required": ["execution_id"]
            }
        ),
        types.Tool(
            name="get_task_output",
            description="Get detailed task-specific output",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {"type": "string", "description": "The execution ID"},
                    "task_id": {"type": "string", "description": "The task ID"}
                },
                "required": ["execution_id", "task_id"]
            }
        ),
        types.Tool(
            name="get_workflow_execution_logs",
            description="Get paginated workflow execution history",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "The workflow ID"},
                    "page": {"type": "integer", "description": "Page number", "default": 1},
                    "per_page": {"type": "integer", "description": "Items per page", "default": 10},
                    "status": {"type": "string", "description": "Filter by status"},
                    "include_logs": {"type": "boolean", "description": "Include log details", "default": True}
                },
                "required": ["workflow_id"]
            }
        ),
        
        # Trigger Management
        types.Tool(
            name="create_trigger",
            description="Create automation triggers (scheduled, manual, webhook)",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Trigger name"},
                    "workflow_id": {"type": "string", "description": "The workflow ID"},
                    "trigger_type": {"type": "string", "description": "Type of trigger"},
                    "schedule": {"type": "string", "description": "Cron schedule (optional)"},
                    "enabled": {"type": "boolean", "description": "Enable trigger", "default": True},
                    "description": {"type": "string", "description": "Trigger description"},
                    "config": {"type": "object", "description": "Trigger configuration"},
                    "input_mapping": {"type": "object", "description": "Input mapping"}
                },
                "required": ["name", "workflow_id", "trigger_type"]
            }
        ),
        types.Tool(
            name="get_all_triggers",
            description="List all triggers with status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="get_trigger",
            description="Get specific trigger details",
            inputSchema={
                "type": "object",
                "properties": {
                    "trigger_id": {"type": "string", "description": "The trigger ID"}
                },
                "required": ["trigger_id"]
            }
        ),
        types.Tool(
            name="get_workflow_triggers",
            description="Get triggers for specific workflow",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "The workflow ID"}
                },
                "required": ["workflow_id"]
            }
        ),
        types.Tool(
            name="update_trigger",
            description="Update trigger settings (schedule, enabled/disabled)",
            inputSchema={
                "type": "object",
                "properties": {
                    "trigger_id": {"type": "string", "description": "The trigger ID"},
                    "name": {"type": "string", "description": "New trigger name"},
                    "schedule": {"type": "string", "description": "New schedule"},
                    "enabled": {"type": "boolean", "description": "Enable/disable trigger"},
                    "description": {"type": "string", "description": "New description"}
                },
                "required": ["trigger_id"]
            }
        ),
        types.Tool(
            name="delete_trigger",
            description="Delete triggers (permanent)",
            inputSchema={
                "type": "object",
                "properties": {
                    "trigger_id": {"type": "string", "description": "The trigger ID"}
                },
                "required": ["trigger_id"]
            }
        ),
        types.Tool(
            name="execute_trigger",
            description="Manually execute triggers with custom inputs",
            inputSchema={
                "type": "object",
                "properties": {
                    "trigger_id": {"type": "string", "description": "The trigger ID"},
                    "inputs": {"type": "object", "description": "Input data for the trigger"}
                },
                "required": ["trigger_id"]
            }
        ),
        
        # System & Monitoring
        types.Tool(
            name="get_workers_status",
            description="Get worker system status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="wait_for_execution_completion",
            description="Wait for execution with real-time monitoring",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {"type": "string", "description": "The execution ID"},
                    "poll_interval": {"type": "integer", "description": "Polling interval in seconds", "default": 5},
                    "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 300},
                    "show_logs": {"type": "boolean", "description": "Show real-time logs", "default": False}
                },
                "required": ["execution_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls"""
    if not workflow_client:
        return [types.TextContent(type="text", text="Error: Workflow client not initialized")]
    
    try:
        # Core Workflow Management
        if name == "create_workflow":
            yaml_content = arguments.get("yaml_content")
            workflow_data = arguments.get("workflow_data")
            result = await workflow_client.create_workflow(yaml_content, workflow_data)
            formatted = workflow_client._format_response(result, "Workflow Created Successfully")
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "get_workflow":
            workflow_id = arguments["workflow_id"]
            result = await workflow_client.get_workflow(workflow_id)
            formatted = workflow_client._format_response(result, f"Workflow Details: {workflow_id}")
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "get_all_workflows":
            result = await workflow_client.get_all_workflows()
            formatted = "=== All Workflows ===\n"
            if isinstance(result, list):
                formatted += f"📋 **Found {len(result)} workflows:**\n\n"
                for workflow in result:
                    name = workflow.get('name', 'Unnamed')
                    workflow_id = workflow.get('id', 'No ID')
                    description = workflow.get('description', 'No description')
                    version = workflow.get('version', 'Unknown')
                    formatted += f"• **{name}** (`{workflow_id}`)\n"
                    formatted += f"  Version: {version}\n"
                    formatted += f"  Description: {description}\n\n"
            
            formatted += f"\n**Raw Data:**\n```json\n{json.dumps(result, indent=2)}\n```"
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "update_workflow":
            workflow_id = arguments["workflow_id"]
            name = arguments.get("name")
            description = arguments.get("description")
            version = arguments.get("version")
            result = await workflow_client.update_workflow(workflow_id, name, description, version)
            formatted = workflow_client._format_response(result, f"Workflow Updated: {workflow_id}")
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "delete_workflow":
            workflow_id = arguments["workflow_id"]
            result = await workflow_client.delete_workflow(workflow_id)
            formatted = f"⚠️ **Workflow Deleted Successfully**\n\nWorkflow ID: {workflow_id}\n\n{json.dumps(result, indent=2)}"
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "get_workflow_dashboard":
            workflow_id = arguments["workflow_id"]
            result = await workflow_client.get_workflow_dashboard(workflow_id)
            formatted = workflow_client._format_response(result, f"Workflow Dashboard: {workflow_id}")
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "validate_workflow_yaml":
            yaml_content = arguments["yaml_content"]
            result = await workflow_client.validate_workflow_yaml(yaml_content)
            formatted = f"✅ **YAML Validation Result**\n\n{json.dumps(result, indent=2)}"
            return [types.TextContent(type="text", text=formatted)]
        
        # Workflow Execution
        elif name == "execute_workflow":
            workflow_id = arguments["workflow_id"]
            inputs = arguments.get("inputs")
            result = await workflow_client.execute_workflow(workflow_id, inputs)
            
            execution_id = result.get("execution_id", "Unknown")
            status = result.get("status", "Unknown")
            
            formatted = f"🚀 **Workflow Execution Started**\n\n"
            formatted += f"• Execution ID: `{execution_id}`\n"
            formatted += f"• Status: {status}\n"
            formatted += f"• Workflow ID: {workflow_id}\n\n"
            formatted += f"**Full Response:**\n```json\n{json.dumps(result, indent=2)}\n```"
            
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "get_workflow_input_format":
            workflow_id = arguments["workflow_id"]
            result = await workflow_client.get_workflow_input_format(workflow_id)
            
            # Extract input format from workflow_data.inputs
            try:
                input_format = result.get("data", {}).get("workflow_data", {}).get("inputs", {})
                if not input_format:
                    input_format = result.get("inputs", {})
                
                if not input_format:
                    input_format = "No input format found for this workflow"
                
                formatted = f"📝 **Workflow Input Format: {workflow_id}**\n\n"
                if isinstance(input_format, dict) or isinstance(input_format, list):
                    formatted += f"```json\n{json.dumps(input_format, indent=2)}\n```"
                else:
                    formatted += str(input_format)
                
                return [types.TextContent(type="text", text=formatted)]
            except Exception as e:
                formatted = f"❌ **Error extracting input format:** {str(e)}\n\n**Full response:**\n```json\n{json.dumps(result, indent=2)}\n```"
                return [types.TextContent(type="text", text=formatted)]
        
        # Execution Monitoring
        elif name == "get_execution_status":
            execution_id = arguments["execution_id"]
            result = await workflow_client.get_execution_status(execution_id)
            
            status = result.get("status", "Unknown")
            workflow_name = result.get("workflow_name", "Unknown")
            started_at = result.get("started_at", "Unknown")
            ended_at = result.get("ended_at", "Not finished")
            
            formatted = f"📊 **Execution Status: {execution_id}**\n\n"
            formatted += f"• Status: **{status}**\n"
            formatted += f"• Workflow: {workflow_name}\n"
            formatted += f"• Started: {started_at}\n"
            formatted += f"• Ended: {ended_at}\n\n"
            
            # Add task summary if available
            execution_data = result.get("execution_data", {})
            if "outputs" in execution_data:
                outputs = execution_data["outputs"]
                formatted += f"📋 **Tasks ({len(outputs)} total):**\n"
                for task_id, task_output in outputs.items():
                    task_status = task_output.get("status", "Unknown")
                    status_icon = "✅" if task_status == "SUCCESS" else "❌" if task_status == "FAILED" else "⏳"
                    formatted += f"   {status_icon} {task_id}: {task_status}\n"
                formatted += "\n"
            
            formatted += f"**Raw Data:**\n```json\n{json.dumps(result, indent=2)}\n```"
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "get_all_executions":
            result = await workflow_client.get_all_executions()
            formatted = "=== All Executions ===\n"
            if isinstance(result, list):
                formatted += f"📋 **Found {len(result)} executions:**\n\n"
                for execution in result:
                    exec_id = execution.get('id', 'No ID')
                    status = execution.get('status', 'Unknown')
                    workflow_name = execution.get('workflow_name', 'Unknown')
                    started_at = execution.get('started_at', 'Unknown')
                    
                    status_icon = "✅" if status == "COMPLETED" else "❌" if status == "FAILED" else "⏳"
                    formatted += f"{status_icon} **{exec_id[:8]}...** ({workflow_name})\n"
                    formatted += f"   Status: {status} | Started: {started_at}\n\n"
            
            formatted += f"\n**Raw Data:**\n```json\n{json.dumps(result, indent=2)}\n```"
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "get_execution_logs":
            execution_id = arguments["execution_id"]
            result = await workflow_client.get_execution_logs(execution_id)
            formatted = workflow_client._format_response(result, f"Execution Logs: {execution_id}")
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "get_task_output":
            execution_id = arguments["execution_id"]
            task_id = arguments["task_id"]
            result = await workflow_client.get_task_output(execution_id, task_id)
            
            task_output = result.get("task_output", {})
            status = task_output.get("status", "Unknown")
            return_code = task_output.get("return_code", "N/A")
            output = task_output.get("output", "No output")
            
            formatted = f"🔧 **Task Output: {task_id}**\n\n"
            formatted += f"• Execution ID: {execution_id}\n"
            formatted += f"• Status: **{status}**\n"
            formatted += f"• Return Code: {return_code}\n"
            formatted += f"• Output Preview: {output[:200]}{'...' if len(output) > 200 else ''}\n\n"
            
            execution_details = task_output.get("execution_details", {})
            if execution_details:
                formatted += f"**Execution Details:**\n"
                formatted += f"• Worker Executed: {execution_details.get('worker_executed', 'N/A')}\n"
                formatted += f"• Message Sent: {execution_details.get('message_sent', 'N/A')}\n\n"
            
            formatted += f"**Raw Data:**\n```json\n{json.dumps(result, indent=2)}\n```"
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "get_workflow_execution_logs":
            workflow_id = arguments["workflow_id"]
            page = arguments.get("page", 1)
            per_page = arguments.get("per_page", 10)
            status = arguments.get("status")
            include_logs = arguments.get("include_logs", True)
            
            result = await workflow_client.get_workflow_execution_logs(workflow_id, page, per_page, status, include_logs)
            formatted = workflow_client._format_response(result, f"Workflow Execution Logs: {workflow_id}")
            return [types.TextContent(type="text", text=formatted)]
        
        # Trigger Management
        elif name == "create_trigger":
            name = arguments["name"]
            workflow_id = arguments["workflow_id"]
            trigger_type = arguments["trigger_type"]
            schedule = arguments.get("schedule")
            enabled = arguments.get("enabled", True)
            description = arguments.get("description")
            config = arguments.get("config")
            input_mapping = arguments.get("input_mapping")
            
            result = await workflow_client.create_trigger(
                name, workflow_id, trigger_type, schedule, enabled, description, config, input_mapping
            )
            formatted = workflow_client._format_response(result, "Trigger Created Successfully")
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "get_all_triggers":
            result = await workflow_client.get_all_triggers()
            formatted = "=== All Triggers ===\n"
            if isinstance(result, list):
                formatted += f"🔗 **Found {len(result)} triggers:**\n\n"
                for trigger in result:
                    name = trigger.get('name', 'Unnamed')
                    trigger_id = trigger.get('id', 'No ID')
                    trigger_type = trigger.get('trigger_type', 'Unknown')
                    enabled = "🟢 Enabled" if trigger.get('enabled') else "🔴 Disabled"
                    workflow_name = trigger.get('workflow_name', 'Unknown Workflow')
                    
                    formatted += f"• **{name}** (`{trigger_id}`)\n"
                    formatted += f"  Type: {trigger_type} | Status: {enabled}\n"
                    formatted += f"  Workflow: {workflow_name}\n\n"
            
            formatted += f"\n**Raw Data:**\n```json\n{json.dumps(result, indent=2)}\n```"
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "get_trigger":
            trigger_id = arguments["trigger_id"]
            result = await workflow_client.get_trigger(trigger_id)
            formatted = workflow_client._format_response(result, f"Trigger Details: {trigger_id}")
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "get_workflow_triggers":
            workflow_id = arguments["workflow_id"]
            result = await workflow_client.get_workflow_triggers(workflow_id)
            formatted = workflow_client._format_response(result, f"Triggers for Workflow: {workflow_id}")
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "update_trigger":
            trigger_id = arguments["trigger_id"]
            name = arguments.get("name")
            schedule = arguments.get("schedule")
            enabled = arguments.get("enabled")
            description = arguments.get("description")
            
            result = await workflow_client.update_trigger(trigger_id, name, schedule, enabled, description)
            formatted = workflow_client._format_response(result, f"Trigger Updated: {trigger_id}")
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "delete_trigger":
            trigger_id = arguments["trigger_id"]
            result = await workflow_client.delete_trigger(trigger_id)
            formatted = f"⚠️ **Trigger Deleted Successfully**\n\nTrigger ID: {trigger_id}\n\n{json.dumps(result, indent=2)}"
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "execute_trigger":
            trigger_id = arguments["trigger_id"]
            inputs = arguments.get("inputs")
            result = await workflow_client.execute_trigger(trigger_id, inputs)
            
            execution_id = result.get("execution_id", "Unknown")
            status = result.get("status", "Unknown")
            
            formatted = f"🔗 **Trigger Executed**\n\n"
            formatted += f"• Trigger ID: {trigger_id}\n"
            formatted += f"• Execution ID: `{execution_id}`\n"
            formatted += f"• Status: {status}\n\n"
            formatted += f"**Full Response:**\n```json\n{json.dumps(result, indent=2)}\n```"
            
            return [types.TextContent(type="text", text=formatted)]
        
        # System & Monitoring
        elif name == "get_workers_status":
            result = await workflow_client.get_workers_status()
            formatted = workflow_client._format_response(result, "Workers Status")
            return [types.TextContent(type="text", text=formatted)]
        
        elif name == "wait_for_execution_completion":
            execution_id = arguments["execution_id"]
            poll_interval = arguments.get("poll_interval", 5)
            timeout = arguments.get("timeout", 300)
            show_logs = arguments.get("show_logs", False)
            
            result = await workflow_client.wait_for_execution_completion(execution_id, poll_interval, timeout, show_logs)
            
            formatted = f"⏳ **Execution Completion Result**\n\n"
            formatted += f"• Execution ID: {execution_id}\n"
            formatted += f"• Poll Interval: {poll_interval} seconds\n"
            formatted += f"• Timeout: {timeout} seconds\n"
            formatted += f"• Show Logs: {show_logs}\n\n"
            
            if result.get("status") == "finished":
                formatted += f"✅ **Execution Finished: {result.get('final_status')}**\n\n"
            else:
                formatted += f"⏰ **Timeout Reached**\n\n"
            
            formatted += "**Status Updates:**\n"
            for update in result.get("status_updates", []):
                formatted += f"{update}\n"
            
            formatted += f"\n**Raw Data:**\n```json\n{json.dumps(result, indent=2)}\n```"
            return [types.TextContent(type="text", text=formatted)]
        
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        logging.error(error_msg)
        return [types.TextContent(type="text", text=error_msg)]

async def main():
    """Main function to run the MCP server"""
    # Initialize the Workflow client
    try:
        initialize_client()
    except Exception as e:
        logging.error(f"Failed to initialize: {e}")
        sys.exit(1)
    
    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="workflow-engine-mcp-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

def run():
    """Run the main function in an asyncio event loop."""
    try:
        asyncio.run(main())
    except Exception as error:
        print(f"Fatal error in main(): {error}", file=sys.stderr)
        sys.exit(1)

