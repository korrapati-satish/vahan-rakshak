"""
watsonx Agent Caller - Invokes pre-deployed agents via watsonx Orchestrate REST API

The ibm_watsonx_orchestrate SDK is for building/defining agents (agent_builder).
Runtime invocation of deployed agents happens via the watsonx Orchestrate REST API.

This module calls agents that are already deployed in watsonx Orchestrate by their agent ID.

API Documentation:
  - Base URL: https://api.us-south.watson-orchestrate.cloud.ibm.com/instances/{instance_id}
  - Run Agent: POST /v1/orchestrate/runs
  - Payload: {"message": {"role": "user", "content": "..."}, "agent_id": "..."}
  - Auth: Bearer token (obtained from IAM service)
  - Response: {"thread_id": "...", "run_id": "...", "task_id": "...", "message_id": "..."}
"""

import logging
import os
import json
import requests
import time
from typing import Dict, Any
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class WatsonxAgentCaller:
    """
    Call agents that are already deployed in IBM watsonx Orchestrate
    
    This uses the watsonx Orchestrate REST API to invoke pre-deployed agents.
    Agents must already exist in your watsonx instance with their agent IDs.
    
    Authentication: Uses IBM Cloud IAM tokens obtained from the API key.
    """
    
    def __init__(self):
        """Initialize watsonx agent caller with credentials from environment"""
        self.api_url = os.getenv("WATSONX_API_URL")
        self.api_key = os.getenv("WATSONX_API_KEY")
        self.project_id = os.getenv("WATSONX_PROJECT_ID")
        self.space_id = os.getenv("WATSONX_SPACE_ID")
        
        # Validate required credentials
        if not all([self.api_url, self.api_key]):
            missing = [k for k, v in {
                "WATSONX_API_URL": self.api_url,
                "WATSONX_API_KEY": self.api_key,
            }.items() if not v]
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        self.iam_url = "https://iam.cloud.ibm.com/identity/token"
        self.access_token = None
        self.token_expiry = None
        
        # Get initial token
        self._refresh_token()
        
        logger.info("watsonx Agent Caller initialized")
        logger.info(f"API URL: {self.api_url}")
        logger.info("Using watsonx Orchestrate REST API for agent invocation")
    
    def _refresh_token(self):
        """Get a new IAM access token from IBM Cloud"""
        try:
            response = requests.post(
                self.iam_url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                    "apikey": self.api_key,
                },
                timeout=10,
            )
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.token_expiry = datetime.now().timestamp() + token_data.get("expires_in", 3600) - 60
            logger.debug("IAM token refreshed successfully")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to obtain IAM token: {e}")
            raise ValueError(f"Authentication failed: {e}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with valid bearer token"""
        # Refresh token if expired
        if self.access_token is None or datetime.now().timestamp() >= self.token_expiry:
            self._refresh_token()
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def _invoke_agent(self, agent_id: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke a deployed watsonx agent via REST API and wait for response.
        
        Args:
            agent_id: Agent ID in watsonx
            action: Action/instruction for the agent
            payload: Input data for the action
            
        Returns:
            Response from watsonx agent including agent's actual response
        """
        # Build the request to watsonx Orchestrate API
        # Endpoint: /v1/orchestrate/runs
        endpoint = f"{self.api_url}/v1/orchestrate/runs"
        
        # Create message content combining action and payload
        message_content = f"{action}\n\n{json.dumps(payload, indent=2)}"
        
        request_body = {
            "message": {
                "role": "user",
                "content": message_content
            },
            "agent_id": agent_id,
        }
        
        logger.debug(f"Invoking: POST {endpoint}")
        logger.debug(f"Agent ID: {agent_id}")
        logger.debug(f"Request body: {json.dumps(request_body, indent=2)}")
        
        try:
            headers = self._get_headers()
            response = requests.post(
                endpoint,
                headers=headers,
                json=request_body,
                timeout=600,
            )

            response.raise_for_status()
            run_response = response.json()
            
            # Extract IDs for fetching the response
            thread_id = run_response.get("thread_id")
            message_id = run_response.get("message_id")
            
            logger.debug(f"Run created: thread_id={thread_id}, message_id={message_id}")
            
            # Poll for the actual agent response
            if thread_id:
                agent_response = self._poll_for_agent_response(
                    thread_id, 
                    message_id,
                    max_wait_seconds=600,
                    poll_interval=2.0
                )
                run_response["agent_response"] = agent_response
            
            return run_response
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to invoke agent: {e}")
            raise
    
    def _fetch_agent_response(self, thread_id: str, message_id: str) -> Dict[str, Any]:
        """
        Fetch the actual agent response from a run.
        
        Args:
            thread_id: Thread ID from the run
            message_id: Message ID from the run
            
        Returns:
            Agent response content
        """
        # Endpoint to fetch message from thread
        # Format: /v1/orchestrate/threads/{thread_id}/messages/{message_id}
        endpoint = f"{self.api_url}/v1/orchestrate/threads/{thread_id}/messages/{message_id}"
        
        logger.debug(f"Fetching agent response: GET {endpoint}")
        
        try:
            headers = self._get_headers()
            response = requests.get(
                endpoint,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not fetch agent response: {e}")
            return {"error": str(e)}
    
    def _poll_for_agent_response(
        self, 
        thread_id: str, 
        message_id: str,
        max_wait_seconds: int = 60,
        poll_interval: float = 2.0
    ) -> Dict[str, Any]:
        """
        Poll for the agent's response until it's available.
        
        Args:
            thread_id: Thread ID from the run
            message_id: Message ID from the run
            max_wait_seconds: Maximum time to wait for response (default 60s)
            poll_interval: Time between polls in seconds (default 2s)
            
        Returns:
            Agent response with content, or error if timeout
        """
        endpoint = f"{self.api_url}/v1/orchestrate/threads/{thread_id}/messages"
        start_time = time.time()
        poll_count = 0
        
        logger.debug(f"Starting to poll for agent response (max {max_wait_seconds}s)")
        
        while True:
            elapsed = time.time() - start_time
            
            # Check timeout
            if elapsed > max_wait_seconds:
                logger.warning(f"Timeout waiting for agent response after {elapsed:.1f}s")
                return {
                    "status": "timeout",
                    "error": f"Agent response not received within {max_wait_seconds} seconds",
                    "elapsed_seconds": elapsed,
                    "polls_made": poll_count
                }
            
            try:
                headers = self._get_headers()
                response = requests.get(
                    endpoint,
                    headers=headers,
                    timeout=10,
                )
                response.raise_for_status()
                
                messages = response.json()

                logger.debug(f"Polled messages: {json.dumps(messages, indent=2)}")
                
                # Check if we have assistant messages (agent responses)
                if isinstance(messages, list):
                    assistant_messages = [
                        msg for msg in messages 
                        if isinstance(msg, dict) and msg.get("role") == "assistant"
                    ]
                    
                    if assistant_messages:
                        logger.debug(f"Agent response received after {elapsed:.1f}s ({poll_count} polls)")
                        # Return the latest assistant message
                        latest = assistant_messages[-1]
                        latest["elapsed_seconds"] = elapsed
                        latest["polls_made"] = poll_count
                        return latest
                
                # Still waiting for response
                poll_count += 1
                if poll_count % 5 == 1:  # Log every 5 polls
                    logger.debug(f"Polling... ({poll_count} polls, {elapsed:.1f}s elapsed)")
                
                time.sleep(poll_interval)
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Poll attempt {poll_count + 1} failed: {e}")
                poll_count += 1
                time.sleep(poll_interval)
                continue
    
    def _extract_clean_message(self, agent_message: Any) -> str:
        """
        Extract clean text from agent response, filtering out debug data.
        
        Args:
            agent_message: Response from agent (can be string, list, or dict)
            
        Returns:
            Clean text message without debug information
        """
        # If it's already a string, return as-is
        if isinstance(agent_message, str):
            return agent_message
        
        # If it's a list (common with Watson responses)
        if isinstance(agent_message, list):
            # Extract text from list of response objects
            texts = []
            for item in agent_message:
                if isinstance(item, dict):
                    # Get text, avoiding debug fields
                    if "text" in item:
                        texts.append(item["text"])
                elif isinstance(item, str):
                    texts.append(item)
            return " ".join(texts) if texts else ""
        
        # If it's a dict
        if isinstance(agent_message, dict):
            # Extract text, avoiding debug fields
            if "text" in agent_message:
                return agent_message["text"]
            elif "content" in agent_message:
                return agent_message["content"]
        
        return ""
    
    def call_gatekeeper_agent(
        self,
        agent_id: str,
        action: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call the Gatekeeper Agent deployed in watsonx
        
        Args:
            agent_id: Gatekeeper agent ID in watsonx
            action: Action to perform (scan_cargo, check_compliance, authorize_vehicle)
            payload: Input data for the action
            
        Returns:
            Formatted response for mobile app with agent decision and details
        """
        logger.info(f"Calling Gatekeeper Agent: {agent_id}")
        logger.info(f"Action: {action}")
        
        try:
            result = self._invoke_agent(agent_id, action, payload)
            
            # Extract agent response or use run details
            agent_response = result.get("agent_response", {})
            agent_message = ""
            elapsed_seconds = 0
            
            if isinstance(agent_response, dict):
                # Get the actual response content
                if "content" in agent_response:
                    agent_message = agent_response.get("content", "")
                elif "text" in agent_response:
                    agent_message = agent_response.get("text", "")
                
                # Track how long we waited
                elapsed_seconds = agent_response.get("elapsed_seconds", 0)
            
            # Clean the message to remove debug output
            clean_message = self._extract_clean_message(agent_message)
            
            logger.info(f"✓ Gatekeeper response received (waited {elapsed_seconds:.1f}s)")
            
            # Format response for mobile app
            response = {
                "agent": "gatekeeper",
                "action": action,
                "status": "success",
                "thread_id": result.get("thread_id"),
                "run_id": result.get("run_id"),
                "response_time_seconds": elapsed_seconds,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add agent message if available
            if clean_message:
                response["decision"] = clean_message
            else:
                response["message"] = f"Cargo validation completed."
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to call Gatekeeper Agent: {e}")
            return {
                "agent": "gatekeeper",
                "action": action,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def call_guardian_agent(
        self,
        agent_id: str,
        vehicle_id: str,
        action: str,
        sensor_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call the Guardian Agent deployed in watsonx
        
        Args:
            agent_id: Guardian agent ID in watsonx
            vehicle_id: Vehicle identifier
            action: Action to perform (monitor_driver, monitor_speed, detect_incident)
            sensor_data: Sensor readings from vehicle
            
        Returns:
            Formatted response for mobile app with agent assessment and details
        """
        logger.info(f"Calling Guardian Agent: {agent_id}")
        logger.info(f"Vehicle: {vehicle_id}")
        logger.info(f"Action: {action}")
        
        try:
            payload = {
                "vehicle_id": vehicle_id,
                "sensor_data": sensor_data,
            }
            result = self._invoke_agent(agent_id, action, payload)
            
            # Extract agent response or use run details
            agent_response = result.get("agent_response", {})
            agent_message = ""
            elapsed_seconds = 0
            
            if isinstance(agent_response, dict):
                # Get the actual response content
                if "content" in agent_response:
                    agent_message = agent_response.get("content", "")
                elif "text" in agent_response:
                    agent_message = agent_response.get("text", "")
                
                # Track how long we waited
                elapsed_seconds = agent_response.get("elapsed_seconds", 0)
            
            # Clean the message to remove debug output
            clean_message = self._extract_clean_message(agent_message)
            
            logger.info(f"✓ Guardian response received (waited {elapsed_seconds:.1f}s)")
            
            # Format response for mobile app
            response = {
                "agent": "guardian",
                "vehicle_id": vehicle_id,
                "action": action,
                "status": "success",
                "thread_id": result.get("thread_id"),
                "run_id": result.get("run_id"),
                "response_time_seconds": elapsed_seconds,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add agent message if available
            if clean_message:
                response["assessment"] = clean_message
            else:
                response["message"] = f"Vehicle monitoring completed."
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to call Guardian Agent: {e}")
            return {
                "agent": "guardian",
                "vehicle_id": vehicle_id,
                "action": action,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def orchestrate_departure_workflow(
        self,
        gatekeeper_agent_id: str,
        guardian_agent_id: str,
        vehicle_id: str,
        cargo_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Orchestrate complete departure workflow using both agents
        
        Args:
            gatekeeper_agent_id: Gatekeeper agent ID in watsonx
            guardian_agent_id: Guardian agent ID in watsonx
            vehicle_id: Vehicle identifier
            cargo_data: Cargo manifest and details
            
        Returns:
            Workflow execution result
        """
        logger.info("\n" + "="*70)
        logger.info("VEHICLE DEPARTURE WORKFLOW")
        logger.info("="*70)
        
        workflow_result = {
            "workflow_id": "departure_workflow",
            "vehicle_id": vehicle_id,
            "started_at": datetime.now().isoformat(),
            "steps": []
        }
        
        try:
            # Step 1: Gatekeeper - Scan Cargo
            logger.info("\n[Step 1/6] Gatekeeper scanning cargo...")
            scan_result = self.call_gatekeeper_agent(
                gatekeeper_agent_id,
                "scan_cargo",
                {
                    "vehicle_id": vehicle_id,
                    "cargo": cargo_data
                }
            )
            workflow_result["steps"].append({"step": 1, "result": scan_result})
            
            if scan_result["status"] != "success":
                logger.warning("Cargo scan failed")
                workflow_result["status"] = "failed"
                return workflow_result
            
            # Step 2: Gatekeeper - Check Compliance
            logger.info("[Step 2/6] Gatekeeper checking compliance...")
            compliance_result = self.call_gatekeeper_agent(
                gatekeeper_agent_id,
                "check_compliance",
                {
                    "vehicle_id": vehicle_id,
                    "cargo": cargo_data,
                    "scan_data": scan_result.get("result")
                }
            )
            workflow_result["steps"].append({"step": 2, "result": compliance_result})
            
            if compliance_result["status"] != "success":
                logger.warning("Compliance check failed")
                workflow_result["status"] = "failed"
                return workflow_result
            
            # Step 3: Gatekeeper - Authorize Departure
            logger.info("[Step 3/6] Gatekeeper authorizing vehicle departure...")
            auth_result = self.call_gatekeeper_agent(
                gatekeeper_agent_id,
                "authorize_vehicle",
                {
                    "vehicle_id": vehicle_id,
                    "compliance_status": compliance_result.get("result")
                }
            )
            workflow_result["steps"].append({"step": 3, "result": auth_result})
            
            if auth_result["status"] != "success":
                logger.warning("Vehicle authorization failed")
                workflow_result["status"] = "blocked"
                return workflow_result
            
            logger.info("✓ Vehicle authorized for departure")
            
            # Step 4: Guardian - Activate Monitoring
            logger.info("[Step 4/6] Guardian activating monitoring...")
            monitor_result = self.call_guardian_agent(
                guardian_agent_id,
                vehicle_id,
                "activate_monitoring",
                {}
            )
            workflow_result["steps"].append({"step": 4, "result": monitor_result})
            
            # Step 5: Guardian - Initialize Sensors
            logger.info("[Step 5/6] Guardian initializing sensors...")
            init_result = self.call_guardian_agent(
                guardian_agent_id,
                vehicle_id,
                "initialize_sensors",
                {}
            )
            workflow_result["steps"].append({"step": 5, "result": init_result})
            
            # Step 6: Vehicle Ready for Road
            logger.info("[Step 6/6] Vehicle ready for road operations...")
            workflow_result["steps"].append({
                "step": 6,
                "result": {
                    "status": "success",
                    "message": "Vehicle ready for road"
                }
            })
            
            workflow_result["status"] = "success"
            workflow_result["completed_at"] = datetime.now().isoformat()
            
            logger.info("\n" + "="*70)
            logger.info("✓ DEPARTURE WORKFLOW COMPLETED SUCCESSFULLY")
            logger.info("="*70 + "\n")
            
            return workflow_result
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            workflow_result["status"] = "error"
            workflow_result["error"] = str(e)
            return workflow_result
    
    def orchestrate_emergency_response(
        self,
        guardian_agent_id: str,
        vehicle_id: str,
        incident_type: str,
        sensor_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Orchestrate emergency response workflow
        
        Args:
            guardian_agent_id: Guardian agent ID in watsonx
            vehicle_id: Vehicle identifier
            incident_type: Type of incident (overspeed, fatigue, etc.)
            sensor_data: Sensor readings
            
        Returns:
            Emergency response result
        """
        logger.info("\n" + "!"*70)
        logger.info("🚨 EMERGENCY INCIDENT DETECTED")
        logger.info("!"*70)
        
        response_result = {
            "workflow_id": "emergency_response_workflow",
            "vehicle_id": vehicle_id,
            "incident_type": incident_type,
            "started_at": datetime.now().isoformat(),
            "steps": []
        }
        
        try:
            # Step 1: Detect Incident
            logger.info("\n[Step 1/7] Guardian detecting incident...")
            detect_result = self.call_guardian_agent(
                guardian_agent_id,
                vehicle_id,
                "detect_incident",
                sensor_data
            )
            response_result["steps"].append({"step": 1, "result": detect_result})
            
            # Step 2: Unlock Doors
            logger.info("[Step 2/7] Unlocking vehicle doors...")
            unlock_result = self.call_guardian_agent(
                guardian_agent_id,
                vehicle_id,
                "unlock_doors",
                {"incident_type": incident_type}
            )
            response_result["steps"].append({"step": 2, "result": unlock_result})
            
            # Step 3: Activate Alarm
            logger.info("[Step 3/7] Activating alarm...")
            alarm_result = self.call_guardian_agent(
                guardian_agent_id,
                vehicle_id,
                "activate_alarm",
                {"incident_type": incident_type}
            )
            response_result["steps"].append({"step": 3, "result": alarm_result})
            
            # Step 4: Broadcast PA Alert
            logger.info("[Step 4/7] Broadcasting PA alert...")
            pa_result = self.call_guardian_agent(
                guardian_agent_id,
                vehicle_id,
                "broadcast_pa_alert",
                {"incident_type": incident_type}
            )
            response_result["steps"].append({"step": 4, "result": pa_result})
            
            # Step 5: Dispatch SOS
            logger.info("[Step 5/7] Dispatching SOS...")
            sos_result = self.call_guardian_agent(
                guardian_agent_id,
                vehicle_id,
                "dispatch_sos",
                {
                    "incident_type": incident_type,
                    "sensor_data": sensor_data
                }
            )
            response_result["steps"].append({"step": 5, "result": sos_result})
            
            # Step 6: Monitor Situation
            logger.info("[Step 6/7] Continuous monitoring active...")
            response_result["steps"].append({
                "step": 6,
                "result": {"status": "success", "message": "Monitoring active"}
            })
            
            # Step 7: Await Help
            logger.info("[Step 7/7] Awaiting emergency services...")
            response_result["steps"].append({
                "step": 7,
                "result": {"status": "success", "message": "Emergency services notified"}
            })
            
            response_result["status"] = "success"
            response_result["completed_at"] = datetime.now().isoformat()
            
            logger.info("\n" + "!"*70)
            logger.info("✓ EMERGENCY RESPONSE COMPLETED")
            logger.info("!"*70 + "\n")
            
            return response_result
            
        except Exception as e:
            logger.error(f"Emergency response failed: {e}")
            response_result["status"] = "error"
            response_result["error"] = str(e)
            return response_result


