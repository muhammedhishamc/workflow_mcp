#!/usr/bin/env python3
"""
Comprehensive Workflow Engine MCP Server using FastMCP

This server provides complete integration with the Workflow Engine API,
including workflow management, execution monitoring, trigger management,
and comprehensive analytics capabilities.

Uses the official MCP Python SDK with FastMCP for simplified development.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Union
import httpx
from mcp.server.fastmcp import FastMCP, Context

# Environment variable for base URL
BASE_URL = os.getenv("WORKFLOW_BASE_URL")
if not BASE_URL:
    raise ValueError("WORKFLOW_BASE_URL is not available in env")
API_BASE_URL = f"{BASE_URL}/api"

# Create FastMCP server instance
mcp = FastMCP("workflow-engine")

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
                
                raise RuntimeError(f"HTTP {response.status_code}: {error_detail}")
            
            # Try to parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError:
                # If response is not JSON, return the text content
                return {"message": response.text, "status_code": response.status_code}
                
    except httpx.TimeoutException:
        raise TimeoutError("Request timed out")
    except httpx.RequestError as e:
        raise ConnectionError(f"Request failed: {str(e)}")

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

# ============ CORE WORKFLOW MANAGEMENT ============

@mcp.tool()
async def create_workflow(
    yaml_content: Optional[str] = None,
    workflow_data: Optional[Dict[str, Any]] = None
) -> str:
    """Create a new workflow using YAML content or workflow data"""
    if not yaml_content and not workflow_data:
        raise ValueError("Either yaml_content or workflow_data is required")
    
    payload = {}
    if yaml_content:
        payload["yaml_content"] = yaml_content
    elif workflow_data:
        payload["workflow_data"] = workflow_data
    
    url = f"{API_BASE_URL}/workflows"
    result = await make_http_request("POST", url, payload)
    
    return format_workflow_response(result, "Workflow Created Successfully")

@mcp.tool()
async def get_workflow(workflow_id: str) -> str:
    """Get detailed workflow information with execution statistics"""
    url = f"{API_BASE_URL}/workflows/{workflow_id}"
    result = await make_http_request("GET", url)
    
    return format_workflow_response(result, f"Workflow Details: {workflow_id}")

@mcp.tool()
async def get_all_workflows() -> str:
    """Get all workflows"""
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
    
    return formatted

@mcp.tool()
async def update_workflow(
    workflow_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    version: Optional[str] = None,
    **kwargs
) -> str:
    """Update an existing workflow's metadata"""
    # Build payload from provided parameters
    payload = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if version is not None:
        payload["version"] = version
    
    # Add any additional kwargs
    payload.update(kwargs)
    
    url = f"{API_BASE_URL}/workflows/{workflow_id}"
    result = await make_http_request("PUT", url, payload)
    
    return format_workflow_response(result, f"Workflow Updated: {workflow_id}")

@mcp.tool()
async def delete_workflow(workflow_id: str) -> str:
    """Delete a workflow by ID (WARNING: This is permanent)"""
    url = f"{API_BASE_URL}/workflows/{workflow_id}"
    result = await make_http_request("DELETE", url)
    
    return f"⚠️ **Workflow Deleted Successfully**\n\nWorkflow ID: {workflow_id}\n\n{json.dumps(result, indent=2)}"

@mcp.tool()
async def get_workflow_dashboard(workflow_id: str) -> str:
    """Get comprehensive workflow dashboard with metrics and analytics"""
    url = f"{API_BASE_URL}/workflows/{workflow_id}/dashboard"
    result = await make_http_request("GET", url)
    
    return format_workflow_response(result, f"Workflow Dashboard: {workflow_id}")

@mcp.tool()
async def validate_workflow_yaml(yaml_content: str) -> str:
    """Validate YAML workflow content before creation"""
    payload = {"yaml_content": yaml_content}
    url = f"{API_BASE_URL}/validate"
    result = await make_http_request("POST", url, payload)
    
    return f"✅ **YAML Validation Result**\n\n{json.dumps(result, indent=2)}"

# ============ WORKFLOW EXECUTION ============

@mcp.tool()
async def execute_workflow(workflow_id: str, inputs: Optional[Dict[str, Any]] = None) -> str:
    """Execute a workflow with provided inputs"""
    if inputs is None:
        inputs = {}
    
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
    
    return formatted

@mcp.tool()
async def get_workflow_input_format(workflow_id: str) -> str:
    """Get the input format/schema for a specific workflow"""
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
        
        return formatted
    except Exception as e:
        return f"❌ **Error extracting input format:** {str(e)}\n\n**Full response:**\n```json\n{json.dumps(result, indent=2)}\n```"

# ============ EXECUTION MONITORING ============

@mcp.tool()
async def get_execution_status(execution_id: str) -> str:
    """Get the status and details of a workflow execution"""
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
    
    return formatted

@mcp.tool()
async def get_all_executions() -> str:
    """Get all workflow executions"""
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
    
    return formatted

@mcp.tool()
async def get_execution_logs(execution_id: str) -> str:
    """Get real-time execution logs with filtering options"""
    url = f"{API_BASE_URL}/executions/{execution_id}/logs"
    result = await make_http_request("GET", url)
    
    return format_workflow_response(result, f"Execution Logs: {execution_id}")

@mcp.tool()
async def get_task_output(execution_id: str, task_id: str) -> str:
    """Get detailed output for a specific task within an execution"""
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
    
    return formatted

@mcp.tool()
async def get_workflow_execution_logs(
    workflow_id: str,
    page: int = 1,
    per_page: int = 10,
    status: Optional[str] = None,
    include_logs: bool = True
) -> str:
    """Get paginated execution logs for a specific workflow"""
    # Build query parameters
    params = {
        "page": page,
        "per_page": per_page,
        "include_logs": str(include_logs).lower()
    }
    if status:
        params["status"] = status
    
    url = f"{API_BASE_URL}/workflows/{workflow_id}/executions/logs"
    result = await make_http_request("GET", url, params=params)
    
    return format_workflow_response(result, f"Workflow Execution Logs: {workflow_id}")

# ============ TRIGGER MANAGEMENT ============

@mcp.tool()
async def create_trigger(
    name: str,
    workflow_id: str,
    trigger_type: str,
    schedule: Optional[str] = None,
    enabled: bool = True,
    description: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    input_mapping: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
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
    
    # Add any additional kwargs
    payload.update(kwargs)
    
    url = f"{API_BASE_URL}/triggers"
    result = await make_http_request("POST", url, payload)
    
    return format_workflow_response(result, "Trigger Created Successfully")

@mcp.tool()
async def get_all_triggers() -> str:
    """Get all triggers"""
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
    
    return formatted

@mcp.tool()
async def get_trigger(trigger_id: str) -> str:
    """Get specific trigger details"""
    url = f"{API_BASE_URL}/triggers/{trigger_id}"
    result = await make_http_request("GET", url)
    
    return format_workflow_response(result, f"Trigger Details: {trigger_id}")

@mcp.tool()
async def get_workflow_triggers(workflow_id: str) -> str:
    """Get all triggers for a specific workflow"""
    url = f"{API_BASE_URL}/workflows/{workflow_id}/triggers"
    result = await make_http_request("GET", url)
    
    return format_workflow_response(result, f"Triggers for Workflow: {workflow_id}")

@mcp.tool()
async def update_trigger(
    trigger_id: str,
    name: Optional[str] = None,
    schedule: Optional[str] = None,
    enabled: Optional[bool] = None,
    description: Optional[str] = None,
    **kwargs
) -> str:
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
    
    # Add any additional kwargs
    payload.update(kwargs)
    
    url = f"{API_BASE_URL}/triggers/{trigger_id}"
    result = await make_http_request("PUT", url, payload)
    
    return format_workflow_response(result, f"Trigger Updated: {trigger_id}")

@mcp.tool()
async def delete_trigger(trigger_id: str) -> str:
    """Delete a trigger by ID (WARNING: This is permanent)"""
    url = f"{API_BASE_URL}/triggers/{trigger_id}"
    result = await make_http_request("DELETE", url)
    
    return f"⚠️ **Trigger Deleted Successfully**\n\nTrigger ID: {trigger_id}\n\n{json.dumps(result, indent=2)}"

@mcp.tool()
async def execute_trigger(trigger_id: str, inputs: Optional[Dict[str, Any]] = None) -> str:
    """Manually execute a trigger with custom inputs"""
    if inputs is None:
        inputs = {}
    
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
    
    return formatted

# ============ SYSTEM AND MONITORING ============

@mcp.tool()
async def get_workers_status() -> str:
    """Get the status of all workflow workers"""
    url = f"{API_BASE_URL}/workers/status"
    result = await make_http_request("GET", url)
    
    return format_workflow_response(result, "Workers Status")

@mcp.tool()
async def wait_for_execution_completion(
    execution_id: str,
    poll_interval: int = 5,
    timeout: int = 300,
    show_logs: bool = False,
    ctx: Optional[Context] = None
) -> str:
    """Wait for a workflow execution to complete with polling"""
    start_time = asyncio.get_event_loop().time()
    last_log_count = 0
    
    formatted = f"⏳ **Waiting for Execution Completion**\n\n"
    formatted += f"• Execution ID: {execution_id}\n"
    formatted += f"• Poll Interval: {poll_interval} seconds\n"
    formatted += f"• Timeout: {timeout} seconds\n"
    formatted += f"• Show Logs: {show_logs}\n\n"
    
    status_updates = []
    
    # Send initial progress if context is available
    if ctx:
        await ctx.info(f"Starting to wait for execution {execution_id}")
    
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        # Get execution status
        status_url = f"{API_BASE_URL}/executions/{execution_id}"
        status_result = await make_http_request("GET", status_url)
        
        current_status = status_result.get("status", "Unknown")
        elapsed_time = asyncio.get_event_loop().time() - start_time
        status_updates.append(f"[{elapsed_time:.1f}s] Status: {current_status}")
        
        # Report progress if context is available
        if ctx:
            progress = min(elapsed_time / timeout, 0.9)  # Cap at 90% until complete
            await ctx.report_progress(
                progress=progress,
                total=1.0,
                message=f"Status: {current_status} (elapsed: {elapsed_time:.1f}s)"
            )
        
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
            
            if ctx:
                await ctx.report_progress(progress=1.0, total=1.0, message=f"Completed: {current_status}")
            
            return formatted
        
        # Wait before next poll
        await asyncio.sleep(poll_interval)
    
    # Timeout reached
    formatted += f"⏰ **Timeout Reached**\n\n"
    formatted += f"Execution did not complete within {timeout} seconds.\n\n"
    formatted += "**Status Updates:**\n"
    for update in status_updates:
        formatted += f"{update}\n"
    
    if ctx:
        await ctx.info(f"Timeout reached waiting for execution {execution_id}")
    
    return formatted

if __name__ == "__main__":
    # Run the server with stdio transport
    mcp.run()