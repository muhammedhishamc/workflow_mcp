#!/usr/bin/env python3
"""
Comprehensive Workflow Engine MCP Server

This server provides complete integration with the Workflow Engine API,
including workflow management, execution monitoring, trigger management,
and comprehensive analytics capabilities.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Union
import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    ErrorCode,
    McpError,
)

# Environment variable for base URL
BASE_URL = os.getenv("WORKFLOW_BASE_URL")
if not BASE_URL:
    raise ValueError("WORKFLOW_BASE_URL is not available in env")
API_BASE_URL = f"{BASE_URL}/api"

server = Server("workflow-engine")

@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List all available workflow engine management tools."""
    return ListToolsResult(
        tools=[
            # Core Workflow Management
            Tool(
                name="create_workflow",
                description="Create a new workflow using YAML content or workflow data",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "yaml_content": {
                            "type": "string",
                            "description": "The YAML content of the workflow to create (as string)"
                        },
                        "workflow_data": {
                            "type": "object",
                            "description": "The workflow data as a structured object (alternative to yaml_content)"
                        }
                    },
                    "additionalProperties": False,
                    "anyOf": [
                        {"required": ["yaml_content"]},
                        {"required": ["workflow_data"]}
                    ]
                }
            ),
            Tool(
                name="get_workflow",
                description="Get detailed workflow information with execution statistics",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The ID of the workflow to retrieve"
                        }
                    },
                    "required": ["workflow_id"]
                }
            ),
            Tool(
                name="get_all_workflows",
                description="Get all workflows",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            ),
            Tool(
                name="update_workflow",
                description="Update an existing workflow's metadata",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The ID of the workflow to update"
                        },
                        "name": {
                            "type": "string",
                            "description": "Updated workflow name"
                        },
                        "description": {
                            "type": "string",
                            "description": "Updated workflow description"
                        },
                        "version": {
                            "type": "string",
                            "description": "Updated workflow version"
                        }
                    },
                    "required": ["workflow_id"],
                    "additionalProperties": True
                }
            ),
            Tool(
                name="delete_workflow",
                description="Delete a workflow by ID (WARNING: This is permanent)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The ID of the workflow to delete"
                        }
                    },
                    "required": ["workflow_id"]
                }
            ),
            Tool(
                name="get_workflow_dashboard",
                description="Get comprehensive workflow dashboard with metrics and analytics",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The ID of the workflow to get dashboard for"
                        }
                    },
                    "required": ["workflow_id"]
                }
            ),
            Tool(
                name="validate_workflow_yaml",
                description="Validate YAML workflow content before creation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "yaml_content": {
                            "type": "string",
                            "description": "The YAML content to validate"
                        }
                    },
                    "required": ["yaml_content"]
                }
            ),
            
            # Workflow Execution
            Tool(
                name="execute_workflow",
                description="Execute a workflow with provided inputs",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The ID of the workflow to execute"
                        },
                        "inputs": {
                            "type": "object",
                            "description": "The input parameters for the workflow execution"
                        }
                    },
                    "required": ["workflow_id"],
                    "additionalProperties": False
                }
            ),
            Tool(
                name="get_workflow_input_format",
                description="Get the input format/schema for a specific workflow",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The ID of the workflow to get input format for"
                        }
                    },
                    "required": ["workflow_id"]
                }
            ),
            
            # Execution Monitoring
            Tool(
                name="get_execution_status",
                description="Get the status and details of a workflow execution",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "The ID of the execution to check"
                        }
                    },
                    "required": ["execution_id"]
                }
            ),
            Tool(
                name="get_all_executions",
                description="Get all workflow executions",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            ),
            Tool(
                name="get_execution_logs",
                description="Get real-time execution logs with filtering options",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "The ID of the execution to get logs for"
                        }
                    },
                    "required": ["execution_id"]
                }
            ),
            Tool(
                name="get_task_output",
                description="Get detailed output for a specific task within an execution",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "The ID of the execution"
                        },
                        "task_id": {
                            "type": "string",
                            "description": "The ID of the task within the execution"
                        }
                    },
                    "required": ["execution_id", "task_id"]
                }
            ),
            Tool(
                name="get_workflow_execution_logs",
                description="Get paginated execution logs for a specific workflow",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The ID of the workflow"
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number (default: 1)",
                            "minimum": 1
                        },
                        "per_page": {
                            "type": "integer",
                            "description": "Items per page (default: 10, max: 100)",
                            "minimum": 1,
                            "maximum": 100
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter by execution status (COMPLETED, FAILED, RUNNING, etc.)"
                        },
                        "include_logs": {
                            "type": "boolean",
                            "description": "Include detailed logs (default: true)"
                        }
                    },
                    "required": ["workflow_id"],
                    "additionalProperties": False
                }
            ),
            
            # Trigger Management
            Tool(
                name="create_trigger",
                description="Create a new trigger for workflow automation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the trigger"
                        },
                        "workflow_id": {
                            "type": "string",
                            "description": "ID of the workflow to trigger"
                        },
                        "trigger_type": {
                            "type": "string",
                            "description": "Type of trigger (scheduled, manual, webhook, etc.)"
                        },
                        "schedule": {
                            "type": "string",
                            "description": "Cron schedule for scheduled triggers"
                        },
                        "enabled": {
                            "type": "boolean",
                            "description": "Whether the trigger is enabled (default: true)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the trigger"
                        },
                        "config": {
                            "type": "object",
                            "description": "Additional trigger configuration"
                        },
                        "input_mapping": {
                            "type": "object",
                            "description": "Input mapping for webhook triggers"
                        }
                    },
                    "required": ["name", "workflow_id", "trigger_type"],
                    "additionalProperties": True
                }
            ),
            Tool(
                name="get_all_triggers",
                description="Get all triggers",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            ),
            Tool(
                name="get_trigger",
                description="Get specific trigger details",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "trigger_id": {
                            "type": "string",
                            "description": "The ID of the trigger to retrieve"
                        }
                    },
                    "required": ["trigger_id"]
                }
            ),
            Tool(
                name="get_workflow_triggers",
                description="Get all triggers for a specific workflow",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The ID of the workflow"
                        }
                    },
                    "required": ["workflow_id"]
                }
            ),
            Tool(
                name="update_trigger",
                description="Update an existing trigger",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "trigger_id": {
                            "type": "string",
                            "description": "The ID of the trigger to update"
                        },
                        "name": {
                            "type": "string",
                            "description": "Updated trigger name"
                        },
                        "schedule": {
                            "type": "string",
                            "description": "Updated cron schedule"
                        },
                        "enabled": {
                            "type": "boolean",
                            "description": "Whether the trigger is enabled"
                        },
                        "description": {
                            "type": "string",
                            "description": "Updated description"
                        }
                    },
                    "required": ["trigger_id"],
                    "additionalProperties": True
                }
            ),
            Tool(
                name="delete_trigger",
                description="Delete a trigger by ID (WARNING: This is permanent)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "trigger_id": {
                            "type": "string",
                            "description": "The ID of the trigger to delete"
                        }
                    },
                    "required": ["trigger_id"]
                }
            ),
            Tool(
                name="execute_trigger",
                description="Manually execute a trigger with custom inputs",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "trigger_id": {
                            "type": "string",
                            "description": "The ID of the trigger to execute"
                        },
                        "inputs": {
                            "type": "object",
                            "description": "Custom inputs for the trigger execution"
                        }
                    },
                    "required": ["trigger_id"],
                    "additionalProperties": False
                }
            ),
            
            # System and Monitoring
            Tool(
                name="get_workers_status",
                description="Get the status of all workflow workers",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            ),
            Tool(
                name="wait_for_execution_completion",
                description="Wait for a workflow execution to complete with polling",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "The ID of the execution to wait for"
                        },
                        "poll_interval": {
                            "type": "integer",
                            "description": "Polling interval in seconds (default: 5)",
                            "minimum": 1,
                            "maximum": 60
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 300)",
                            "minimum": 30,
                            "maximum": 3600
                        },
                        "show_logs": {
                            "type": "boolean",
                            "description": "Show real-time logs while waiting (default: false)"
                        }
                    },
                    "required": ["execution_id"],
                    "additionalProperties": False
                }
            )
        ]
    )

async def make_http_request(
    method: str, 
    url: str, 
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Make an HTTP request with proper error handling."""
    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                json=payload,
                headers=default_headers,
                params=params,
                timeout=30.0
            )
            
            # Check if the response is successful
            if response.status_code >= 400:
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = json.dumps(error_data, indent=2)
                except:
                    error_detail = response.text
                
                raise McpError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"HTTP {response.status_code}: {error_detail}"
                )
            
            # Try to parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError:
                # If response is not JSON, return the text content
                return {"message": response.text, "status_code": response.status_code}
                
    except httpx.TimeoutException:
        raise McpError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Request timed out"
        )
    except httpx.RequestError as e:
        raise McpError(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Request failed: {str(e)}"
        )

def format_workflow_response(data: Dict[str, Any], title: str) -> str:
    """Format workflow response data for better readability."""
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

@server.call_tool()
async def call_tool(request: CallToolRequest) -> CallToolResult:
    """Handle tool calls for workflow engine operations."""
    
    try:
        tool_name = request.params.name
        args = request.params.arguments
        
        # ============ CORE WORKFLOW MANAGEMENT ============
        
        if tool_name == "create_workflow":
            yaml_content = args.get("yaml_content")
            workflow_data = args.get("workflow_data")
            
            if not yaml_content and not workflow_data:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="Either yaml_content or workflow_data is required")
            
            payload = {}
            if yaml_content:
                payload["yaml_content"] = yaml_content
            elif workflow_data:
                payload["workflow_data"] = workflow_data
            
            url = f"{API_BASE_URL}/workflows"
            result = await make_http_request("POST", url, payload)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_workflow_response(result, "Workflow Created Successfully")
                )]
            )
        
        elif tool_name == "get_workflow":
            workflow_id = args.get("workflow_id")
            if not workflow_id:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="workflow_id is required")
            
            url = f"{API_BASE_URL}/workflows/{workflow_id}"
            result = await make_http_request("GET", url)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_workflow_response(result, f"Workflow Details: {workflow_id}")
                )]
            )
        
        elif tool_name == "get_all_workflows":
            url = f"{API_BASE_URL}/workflows"
            result = await make_http_request("GET", url)
            
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
            
            return CallToolResult(
                content=[TextContent(type="text", text=formatted)]
            )
        
        elif tool_name == "update_workflow":
            workflow_id = args.get("workflow_id")
            if not workflow_id:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="workflow_id is required")
            
            # Remove workflow_id from args for the payload
            payload = {k: v for k, v in args.items() if k != "workflow_id"}
            
            url = f"{API_BASE_URL}/workflows/{workflow_id}"
            result = await make_http_request("PUT", url, payload)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_workflow_response(result, f"Workflow Updated: {workflow_id}")
                )]
            )
        
        elif tool_name == "delete_workflow":
            workflow_id = args.get("workflow_id")
            if not workflow_id:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="workflow_id is required")
            
            url = f"{API_BASE_URL}/workflows/{workflow_id}"
            result = await make_http_request("DELETE", url)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"⚠️ **Workflow Deleted Successfully**\n\nWorkflow ID: {workflow_id}\n\n{json.dumps(result, indent=2)}"
                )]
            )
        
        elif tool_name == "get_workflow_dashboard":
            workflow_id = args.get("workflow_id")
            if not workflow_id:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="workflow_id is required")
            
            url = f"{API_BASE_URL}/workflows/{workflow_id}/dashboard"
            result = await make_http_request("GET", url)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_workflow_response(result, f"Workflow Dashboard: {workflow_id}")
                )]
            )
        
        elif tool_name == "validate_workflow_yaml":
            yaml_content = args.get("yaml_content")
            if not yaml_content:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="yaml_content is required")
            
            payload = {"yaml_content": yaml_content}
            url = f"{API_BASE_URL}/validate"
            result = await make_http_request("POST", url, payload)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"✅ **YAML Validation Result**\n\n{json.dumps(result, indent=2)}"
                )]
            )
        
        # ============ WORKFLOW EXECUTION ============
        
        elif tool_name == "execute_workflow":
            workflow_id = args.get("workflow_id")
            inputs = args.get("inputs", {})
            
            if not workflow_id:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="workflow_id is required")
            
            url = f"{API_BASE_URL}/workflows/{workflow_id}/execute"
            payload = {"inputs": inputs}
            result = await make_http_request("POST", url, payload)
            
            execution_id = result.get("execution_id", "Unknown")
            status = result.get("status", "Unknown")
            
            formatted = f"🚀 **Workflow Execution Started**\n\n"
            formatted += f"• Execution ID: `{execution_id}`\n"
            formatted += f"• Status: {status}\n"
            formatted += f"• Workflow ID: {workflow_id}\n\n"
            formatted += f"**Full Response:**\n```json\n{json.dumps(result, indent=2)}\n```"
            
            return CallToolResult(
                content=[TextContent(type="text", text=formatted)]
            )
        
        elif tool_name == "get_workflow_input_format":
            workflow_id = args.get("workflow_id")
            if not workflow_id:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="workflow_id is required")
            
            url = f"{API_BASE_URL}/workflows/{workflow_id}"
            result = await make_http_request("GET", url)
            
            # Extract input format from workflow_data.inputs
            try:
                input_format = result.get("data", {}).get("workflow_data", {}).get("inputs", {})
                if not input_format:
                    # Also check root level inputs
                    input_format = result.get("inputs", {})
                
                if not input_format:
                    input_format = "No input format found for this workflow"
                
                formatted = f"📝 **Workflow Input Format: {workflow_id}**\n\n"
                if isinstance(input_format, dict) or isinstance(input_format, list):
                    formatted += f"```json\n{json.dumps(input_format, indent=2)}\n```"
                else:
                    formatted += str(input_format)
                
                return CallToolResult(
                    content=[TextContent(type="text", text=formatted)]
                )
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ **Error extracting input format:** {str(e)}\n\n**Full response:**\n```json\n{json.dumps(result, indent=2)}\n```"
                    )]
                )
        
        # ============ EXECUTION MONITORING ============
        
        elif tool_name == "get_execution_status":
            execution_id = args.get("execution_id")
            if not execution_id:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="execution_id is required")
            
            url = f"{API_BASE_URL}/executions/{execution_id}"
            result = await make_http_request("GET", url)
            
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
            
            return CallToolResult(
                content=[TextContent(type="text", text=formatted)]
            )
        
        elif tool_name == "get_all_executions":
            url = f"{API_BASE_URL}/executions"
            result = await make_http_request("GET", url)
            
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
            
            return CallToolResult(
                content=[TextContent(type="text", text=formatted)]
            )
        
        elif tool_name == "get_execution_logs":
            execution_id = args.get("execution_id")
            if not execution_id:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="execution_id is required")
            
            url = f"{API_BASE_URL}/executions/{execution_id}/logs"
            result = await make_http_request("GET", url)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_workflow_response(result, f"Execution Logs: {execution_id}")
                )]
            )
        
        elif tool_name == "get_task_output":
            execution_id = args.get("execution_id")
            task_id = args.get("task_id")
            
            if not execution_id or not task_id:
                raise McpError(
                    code=ErrorCode.INVALID_PARAMS, 
                    message="Both execution_id and task_id are required"
                )
            
            url = f"{API_BASE_URL}/executions/{execution_id}/tasks/{task_id}"
            result = await make_http_request("GET", url)
            
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
            
            return CallToolResult(
                content=[TextContent(type="text", text=formatted)]
            )
        
        elif tool_name == "get_workflow_execution_logs":
            workflow_id = args.get("workflow_id")
            if not workflow_id:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="workflow_id is required")
            
            # Build query parameters
            params = {}
            if "page" in args:
                params["page"] = args["page"]
            if "per_page" in args:
                params["per_page"] = args["per_page"]
            if "status" in args:
                params["status"] = args["status"]
            if "include_logs" in args:
                params["include_logs"] = str(args["include_logs"]).lower()
            
            url = f"{API_BASE_URL}/workflows/{workflow_id}/executions/logs"
            result = await make_http_request("GET", url, params=params)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_workflow_response(result, f"Workflow Execution Logs: {workflow_id}")
                )]
            )
        
        # ============ TRIGGER MANAGEMENT ============
        
        elif tool_name == "create_trigger":
            name = args.get("name")
            workflow_id = args.get("workflow_id")
            trigger_type = args.get("trigger_type")
            
            if not all([name, workflow_id, trigger_type]):
                raise McpError(
                    code=ErrorCode.INVALID_PARAMS, 
                    message="name, workflow_id, and trigger_type are required"
                )
            
            url = f"{API_BASE_URL}/triggers"
            result = await make_http_request("POST", url, args)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_workflow_response(result, "Trigger Created Successfully")
                )]
            )
        
        elif tool_name == "get_all_triggers":
            url = f"{API_BASE_URL}/triggers"
            result = await make_http_request("GET", url)
            
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
            
            return CallToolResult(
                content=[TextContent(type="text", text=formatted)]
            )
        
        elif tool_name == "get_trigger":
            trigger_id = args.get("trigger_id")
            if not trigger_id:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="trigger_id is required")
            
            url = f"{API_BASE_URL}/triggers/{trigger_id}"
            result = await make_http_request("GET", url)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_workflow_response(result, f"Trigger Details: {trigger_id}")
                )]
            )
        
        elif tool_name == "get_workflow_triggers":
            workflow_id = args.get("workflow_id")
            if not workflow_id:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="workflow_id is required")
            
            url = f"{API_BASE_URL}/workflows/{workflow_id}/triggers"
            result = await make_http_request("GET", url)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_workflow_response(result, f"Triggers for Workflow: {workflow_id}")
                )]
            )
        
        elif tool_name == "update_trigger":
            trigger_id = args.get("trigger_id")
            if not trigger_id:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="trigger_id is required")
            
            # Remove trigger_id from args for the payload
            payload = {k: v for k, v in args.items() if k != "trigger_id"}
            
            url = f"{API_BASE_URL}/triggers/{trigger_id}"
            result = await make_http_request("PUT", url, payload)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_workflow_response(result, f"Trigger Updated: {trigger_id}")
                )]
            )
        
        elif tool_name == "delete_trigger":
            trigger_id = args.get("trigger_id")
            if not trigger_id:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="trigger_id is required")
            
            url = f"{API_BASE_URL}/triggers/{trigger_id}"
            result = await make_http_request("DELETE", url)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"⚠️ **Trigger Deleted Successfully**\n\nTrigger ID: {trigger_id}\n\n{json.dumps(result, indent=2)}"
                )]
            )
        
        elif tool_name == "execute_trigger":
            trigger_id = args.get("trigger_id")
            inputs = args.get("inputs", {})
            
            if not trigger_id:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="trigger_id is required")
            
            url = f"{API_BASE_URL}/triggers/{trigger_id}/execute"
            payload = {"inputs": inputs}
            result = await make_http_request("POST", url, payload)
            
            execution_id = result.get("execution_id", "Unknown")
            status = result.get("status", "Unknown")
            
            formatted = f"🔗 **Trigger Executed**\n\n"
            formatted += f"• Trigger ID: {trigger_id}\n"
            formatted += f"• Execution ID: `{execution_id}`\n"
            formatted += f"• Status: {status}\n\n"
            formatted += f"**Full Response:**\n```json\n{json.dumps(result, indent=2)}\n```"
            
            return CallToolResult(
                content=[TextContent(type="text", text=formatted)]
            )
        
        # ============ SYSTEM AND MONITORING ============
        
        elif tool_name == "get_workers_status":
            url = f"{API_BASE_URL}/workers/status"
            result = await make_http_request("GET", url)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=format_workflow_response(result, "Workers Status")
                )]
            )
        
        elif tool_name == "wait_for_execution_completion":
            execution_id = args.get("execution_id")
            if not execution_id:
                raise McpError(code=ErrorCode.INVALID_PARAMS, message="execution_id is required")
            
            poll_interval = args.get("poll_interval", 5)
            timeout = args.get("timeout", 300)
            show_logs = args.get("show_logs", False)
            
            start_time = asyncio.get_event_loop().time()
            last_log_count = 0
            
            formatted = f"⏳ **Waiting for Execution Completion**\n\n"
            formatted += f"• Execution ID: {execution_id}\n"
            formatted += f"• Poll Interval: {poll_interval} seconds\n"
            formatted += f"• Timeout: {timeout} seconds\n"
            formatted += f"• Show Logs: {show_logs}\n\n"
            
            status_updates = []
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                # Get execution status
                status_url = f"{API_BASE_URL}/executions/{execution_id}"
                status_result = await make_http_request("GET", status_url)
                
                current_status = status_result.get("status", "Unknown")
                status_updates.append(f"[{asyncio.get_event_loop().time() - start_time:.1f}s] Status: {current_status}")
                
                # Show real-time logs if requested
                if show_logs:
                    try:
                        logs_url = f"{API_BASE_URL}/executions/{execution_id}/logs"
                        logs_result = await make_http_request("GET", logs_url)
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
                    formatted += f"✅ **Execution Finished: {current_status}**\n\n"
                    formatted += "**Status Updates:**\n"
                    for update in status_updates:
                        formatted += f"{update}\n"
                    formatted += "\n"
                    formatted += f"**Final Status:**\n```json\n{json.dumps(status_result, indent=2)}\n```"
                    
                    return CallToolResult(
                        content=[TextContent(type="text", text=formatted)]
                    )
                
                # Wait before next poll
                await asyncio.sleep(poll_interval)
            
            # Timeout reached
            formatted += f"⏰ **Timeout Reached**\n\n"
            formatted += f"Execution did not complete within {timeout} seconds.\n\n"
            formatted += "**Status Updates:**\n"
            for update in status_updates:
                formatted += f"{update}\n"
            
            return CallToolResult(
                content=[TextContent(type="text", text=formatted)]
            )
        
        else:
            raise McpError(
                code=ErrorCode.METHOD_NOT_FOUND,
                message=f"Unknown tool: {tool_name}"
            )
    
    except McpError:
        # Re-raise MCP errors as-is
        raise
    except Exception as e:
        # Convert other exceptions to MCP errors
        raise McpError(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Unexpected error in {request.params.name}: {str(e)}"
        )

async def main_async():
    """Run the MCP server."""
    # Server configuration
    options = InitializationOptions(
        server_name="workflow-engine",
        server_version="2.0.0",
        capabilities={}
    )
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            options
        )

def main():
    asyncio.run(main_async())