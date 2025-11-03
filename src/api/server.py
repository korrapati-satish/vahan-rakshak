"""
FastAPI backend for Vāhan-Rakshak
- Receives driver monitoring and speed sensor data from mobile/IoT
- Exposes vehicle status, incidents, and alerts

Behavior:
- If WATSONX_ENABLED=true (or 1/yes/on), API delegates to watsonx Orchestrate agents
    using WatsonxAgentCaller and configured agent/action IDs via environment variables.
- Otherwise, API falls back to the in-repo GuardianAgent for local development and tests.
"""

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import json
from pathlib import Path

from src.watsonx_agent_caller import WatsonxAgentCaller
from src.tools.cargo_scanner import CargoScanner
from src.tools.regulator_api import RegulatorAPI
from src.tools.safety_actuator import SafetyActuator
from src.tools.sos_dispatcher import SOSDispatcher
from src.tools.speed_detector import SpeedDetector

logger = logging.getLogger(__name__)

app = FastAPI(title="Vahan-Rakshak API", version="1.0.0")

# watsonx delegation config
WATSONX_ENABLED: bool = True  # Always delegate to watsonx as per requirement
GUARDIAN_AGENT_ID: str = os.getenv("GUARDIAN_AGENT_ID", "guardian_v1")
WATSONX_GUARDIAN_ACTION_MONITOR: str = os.getenv("WATSONX_GUARDIAN_ACTION_MONITOR", "monitor_driver")
WATSONX_GUARDIAN_ACTION_SPEED: str = os.getenv("WATSONX_GUARDIAN_ACTION_SPEED", "monitor_speed")
GATEKEEPER_AGENT_ID: str = os.getenv("GATEKEEPER_AGENT_ID", "gatekeeper_v1")

_wx_caller: Optional[WatsonxAgentCaller] = None
try:
    _wx_caller = WatsonxAgentCaller()
    logger.info("✓ watsonx delegation ENABLED; server will call remote agents")
except Exception as e:
    logger.error(f"❌ Failed to initialize WatsonxAgentCaller: {e}")
    logger.error(f"   Make sure these environment variables are set:")
    logger.error(f"   - WATSONX_API_URL")
    logger.error(f"   - WATSONX_API_KEY")
    logger.error(f"   - GATEKEEPER_AGENT_ID (optional)")
    logger.error(f"   - GUARDIAN_AGENT_ID (optional)")
    _wx_caller = None

# Per-vehicle tool registries (stateful tools)
_safety_tools: Dict[str, SafetyActuator] = {}
_sos_tools: Dict[str, SOSDispatcher] = {}
_speed_tools: Dict[str, SpeedDetector] = {}


def _get_safety(vehicle_id: str) -> SafetyActuator:
    if not vehicle_id:
        raise HTTPException(status_code=400, detail="vehicle_id is required")
    if vehicle_id not in _safety_tools:
        _safety_tools[vehicle_id] = SafetyActuator()
    return _safety_tools[vehicle_id]


def _get_sos(vehicle_id: str) -> SOSDispatcher:
    if not vehicle_id:
        raise HTTPException(status_code=400, detail="vehicle_id is required")
    if vehicle_id not in _sos_tools:
        _sos_tools[vehicle_id] = SOSDispatcher()
    return _sos_tools[vehicle_id]


def _get_speed(vehicle_id: str) -> SpeedDetector:
    if not vehicle_id:
        raise HTTPException(status_code=400, detail="vehicle_id is required")
    if vehicle_id not in _speed_tools:
        _speed_tools[vehicle_id] = SpeedDetector()
    return _speed_tools[vehicle_id]


def _get_swagger_json_path() -> Path:
    """Resolve absolute path to docs/swagger.json bundled with the repo."""
    here = Path(__file__).resolve()
    # src/api/server.py -> go up two levels to repo root, then docs/swagger.json
    swagger_path = here.parent.parent.parent / "docs" / "swagger.json"
    return swagger_path


def _require_caller() -> WatsonxAgentCaller:
    if _wx_caller is None:
        raise HTTPException(
            status_code=503, 
            detail="Watson Orchestrate not configured. Missing required environment variables: WATSONX_API_URL and WATSONX_API_KEY"
        )
    return _wx_caller


class DriverMonitoringRequest(BaseModel):
    vehicle_id: str = Field(..., description="Vehicle identifier")
    eye_closure_pct: float = Field(..., ge=0, le=100)
    blink_duration_ms: float = Field(..., gt=0)
    yawning_rate_per_min: float = Field(..., ge=0)
    steering_variability: float = Field(..., ge=0, le=1)
    lane_departures: int = Field(..., ge=0)


class SpeedReadingRequest(BaseModel):
    vehicle_id: str
    current_speed_kmh: float = Field(..., ge=0)
    speed_limit_kmh: float = Field(..., gt=0)
    timestamp_ms: Optional[int] = None


class GatekeeperInvokeRequest(BaseModel):
    action: str = Field(..., description="Gatekeeper action name (e.g., scan_cargo, check_compliance, authorize_vehicle)")
    payload: Dict[str, Any] = Field(..., description="Structured input payload with required fields. For scan_cargo: include vehicle_id, vehicle_class, vehicle_number, driver_name, cargo (with description, weight_kg, hazmat), etc.")


# ============ Tool API Contracts ============

class CargoScanQrRequest(BaseModel):
    qr_data: str


class CargoCreateManifestRequest(BaseModel):
    manifest_id: str
    vehicle_id: str
    vehicle_number: str
    driver_name: str
    scanned_by: str
    items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of scanned item dicts (fields like item_id, name, cargo_type, quantity, weight_kg, hazmat_code, qr_code)",
    )


class RegulatorCargoComplianceRequest(BaseModel):
    vehicle_class: str
    cargo_types: List[str]


class RegulatorWeightRequest(BaseModel):
    vehicle_class: str
    total_weight_kg: float


class RegulatorSensorsRequest(BaseModel):
    vehicle_class: str
    installed_sensors: List[str]


class RegulatorPermitRequest(BaseModel):
    vehicle_id: str
    route: str
    cargo_type: str


class RegulatorReportViolationRequest(BaseModel):
    vehicle_id: str
    violation_type: str
    timestamp: str


class SafetyPARequest(BaseModel):
    message: str
    language: str = "en"


class SafetyDriverAlertRequest(BaseModel):
    intensity: str = "high"


class SafetySeatVibrationRequest(BaseModel):
    intensity: str = "high"
    duration_s: int = Field(2, ge=1, le=30)


class SafetyLightsRequest(BaseModel):
    pattern: str = "fast"


class SafetyEmergencyRequest(BaseModel):
    incident_type: str


class SOSAlertRequest(BaseModel):
    vehicle_id: str
    incident_type: str
    location: Optional[Dict[str, float]] = None
    details: Optional[Dict[str, Any]] = None


class SOSLocationUpdateRequest(BaseModel):
    vehicle_id: str
    lat: float
    lon: float
    alt: Optional[float] = None


class SOSFleetNotifyRequest(BaseModel):
    vehicle_id: str
    message: str


@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/openapi-examples.json")
async def get_openapi_examples() -> Dict[str, Any]:
    """Serve the curated Swagger (OpenAPI) JSON with examples from docs/swagger.json.

    This exists alongside FastAPI's autogenerated /openapi.json and /docs. Use this
    endpoint when you want the version with comprehensive examples.
    """
    swagger_path = _get_swagger_json_path()
    if not swagger_path.exists():
        raise HTTPException(status_code=404, detail="Swagger JSON not found")
    try:
        with swagger_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load swagger.json: {e}")
        raise HTTPException(status_code=500, detail="Failed to load swagger JSON")


@app.post("/v1/driver/monitoring")
async def post_driver_monitoring(payload: DriverMonitoringRequest) -> Dict[str, Any]:
    caller = _require_caller()
    sensor_data = {
        "eye_closure_pct": payload.eye_closure_pct,
        "blink_duration_ms": payload.blink_duration_ms,
        "yawning_rate_per_min": payload.yawning_rate_per_min,
        "steering_variability": payload.steering_variability,
        "lane_departures": payload.lane_departures,
    }
    res = caller.call_guardian_agent(
        agent_id=GUARDIAN_AGENT_ID,
        vehicle_id=payload.vehicle_id,
        action=WATSONX_GUARDIAN_ACTION_MONITOR,
        sensor_data=sensor_data,
    )
    # Return the full agent response with assessment/decision
    return res


@app.post("/v1/gatekeeper/run")
async def post_gatekeeper_run(body: GatekeeperInvokeRequest) -> Dict[str, Any]:
    """Invoke the watsonx Gatekeeper agent with a specified action and payload."""
    caller = _require_caller()
    res = caller.call_gatekeeper_agent(
        agent_id=GATEKEEPER_AGENT_ID,
        action=body.action,
        payload=body.payload,
    )
    # Return the full agent response with decision field
    return res


@app.post("/v1/speed")
async def post_speed_reading(payload: SpeedReadingRequest) -> Dict[str, Any]:
    caller = _require_caller()
    sensor_data = {
        "current_speed_kmh": payload.current_speed_kmh,
        "speed_limit_kmh": payload.speed_limit_kmh,
        "timestamp_ms": payload.timestamp_ms or int(datetime.now().timestamp() * 1000),
    }
    res = caller.call_guardian_agent(
        agent_id=GUARDIAN_AGENT_ID,
        vehicle_id=payload.vehicle_id,
        action=WATSONX_GUARDIAN_ACTION_SPEED,
        sensor_data=sensor_data,
    )
    # Return the full agent response with assessment/decision
    return res


# ============ Cargo Scanner ============

@app.post("/v1/tools/cargo/scan-qr")
async def tool_cargo_scan_qr(body: CargoScanQrRequest) -> Dict[str, Any]:
    scanner = CargoScanner()
    return scanner.scan_qr_code(body.qr_data)


@app.post("/v1/tools/cargo/create-manifest")
async def tool_cargo_create_manifest(body: CargoCreateManifestRequest) -> Dict[str, Any]:
    scanner = CargoScanner()
    # seed scanned_items from provided items list
    scanner.scanned_items = body.items
    print(f"Creating manifest with items: {json.dumps(body.items)}")
    manifest = scanner.create_manifest(
        manifest_id=body.manifest_id,
        vehicle_id=body.vehicle_id,
        vehicle_number=body.vehicle_number,
        driver_name=body.driver_name,
        scanned_by=body.scanned_by,
    )
    return manifest.model_dump()


# ============ Regulator API ============

@app.post("/v1/tools/regulator/check-cargo-compliance")
async def tool_reg_check_cargo(body: RegulatorCargoComplianceRequest) -> Dict[str, Any]:
    api = RegulatorAPI()
    return api.check_cargo_compliance(body.vehicle_class, body.cargo_types)


@app.post("/v1/tools/regulator/check-weight")
async def tool_reg_check_weight(body: RegulatorWeightRequest) -> Dict[str, Any]:
    api = RegulatorAPI()
    return api.check_weight_compliance(body.vehicle_class, body.total_weight_kg)


@app.post("/v1/tools/regulator/check-sensors")
async def tool_reg_check_sensors(body: RegulatorSensorsRequest) -> Dict[str, Any]:
    api = RegulatorAPI()
    return api.check_sensor_requirements(body.vehicle_class, body.installed_sensors)


@app.post("/v1/tools/regulator/verify-permit")
async def tool_reg_verify_permit(body: RegulatorPermitRequest) -> Dict[str, Any]:
    api = RegulatorAPI()
    return api.verify_transport_permit(body.vehicle_id, body.route, body.cargo_type)


@app.post("/v1/tools/regulator/report-violation")
async def tool_reg_report_violation(body: RegulatorReportViolationRequest) -> Dict[str, Any]:
    api = RegulatorAPI()
    api.report_violation(body.vehicle_id, body.violation_type, body.timestamp)
    logger.info(f"Violation recorded: {body.vehicle_id} - {body.violation_type} has been sent to regulator.")
    return {"status": "recorded"}


@app.get("/v1/tools/regulator/violations/{vehicle_id}")
async def tool_reg_get_violations(vehicle_id: str) -> List[Dict[str, Any]]:
    api = RegulatorAPI()
    return api.get_violation_history(vehicle_id)


# ============ Safety Actuator ============

@app.post("/v1/tools/safety/{vehicle_id}/unlock-doors")
async def tool_safety_unlock_doors(vehicle_id: str) -> Dict[str, Any]:
    return _get_safety(vehicle_id).unlock_all_doors()


@app.post("/v1/tools/safety/{vehicle_id}/alarm")
async def tool_safety_alarm(vehicle_id: str) -> Dict[str, Any]:
    return _get_safety(vehicle_id).activate_emergency_alarm()


@app.post("/v1/tools/safety/{vehicle_id}/pa")
async def tool_safety_pa(vehicle_id: str, body: SafetyPARequest) -> Dict[str, Any]:
    return _get_safety(vehicle_id).activate_pa_system(body.message, body.language)


@app.post("/v1/tools/safety/{vehicle_id}/lights")
async def tool_safety_lights(vehicle_id: str, body: SafetyLightsRequest) -> Dict[str, Any]:
    return _get_safety(vehicle_id).activate_emergency_lighting() if body.pattern else _get_safety(vehicle_id).activate_emergency_lighting()


@app.post("/v1/tools/safety/{vehicle_id}/driver-alert")
async def tool_safety_driver_alert(vehicle_id: str, body: SafetyDriverAlertRequest) -> Dict[str, Any]:
    return _get_safety(vehicle_id).play_driver_alert_tone(body.intensity)


@app.post("/v1/tools/safety/{vehicle_id}/seat-vibration")
async def tool_safety_seat_vibration(vehicle_id: str, body: SafetySeatVibrationRequest) -> Dict[str, Any]:
    return _get_safety(vehicle_id).seat_vibration(body.intensity, body.duration_s)


@app.post("/v1/tools/safety/{vehicle_id}/flash-lights")
async def tool_safety_flash_lights(vehicle_id: str, body: SafetyLightsRequest) -> Dict[str, Any]:
    return _get_safety(vehicle_id).flash_cabin_lights(body.pattern)


@app.post("/v1/tools/safety/{vehicle_id}/emergency")
async def tool_safety_emergency(vehicle_id: str, body: SafetyEmergencyRequest) -> Dict[str, Any]:
    return _get_safety(vehicle_id).execute_emergency_response(body.incident_type)


@app.post("/v1/tools/safety/{vehicle_id}/deactivate")
async def tool_safety_deactivate(vehicle_id: str) -> Dict[str, Any]:
    return _get_safety(vehicle_id).deactivate_emergency_systems()


@app.get("/v1/tools/safety/{vehicle_id}/actions")
async def tool_safety_actions(vehicle_id: str) -> List[Dict[str, Any]]:
    return _get_safety(vehicle_id).get_actions_log()


@app.get("/v1/tools/safety/{vehicle_id}/status")
async def tool_safety_status(vehicle_id: str) -> Dict[str, Any]:
    return _get_safety(vehicle_id).get_system_status()


# ============ SOS Dispatcher ============

@app.post("/v1/tools/sos/send-alert")
async def tool_sos_send_alert(body: SOSAlertRequest) -> Dict[str, Any]:
    sos = _get_sos(body.vehicle_id)
    return sos.send_sos_alert(body.vehicle_id, body.incident_type, body.location or {}, body.details or {})


@app.post("/v1/tools/sos/gps-update")
async def tool_sos_gps_update(body: SOSLocationUpdateRequest) -> Dict[str, Any]:
    sos = _get_sos(body.vehicle_id)
    return sos.send_gps_location_update(body.vehicle_id, body.lat, body.lon, body.alt)


@app.post("/v1/tools/sos/notify-fleet")
async def tool_sos_notify_fleet(body: SOSFleetNotifyRequest) -> Dict[str, Any]:
    sos = _get_sos(body.vehicle_id)
    # Backwards-compatible mapping: our SOSDispatcher expects (vehicle_id, incident_type, incident_details, contact_info)
    # but the API contract currently sends just a message. Use sensible defaults for missing fields.
    contact = os.getenv("FLEET_CONTACT", "fleet@company.com")
    return sos.notify_fleet_manager(
        vehicle_id=body.vehicle_id,
        incident_type="INFO",
        incident_details=body.message,
        contact_info=contact,
    )


@app.get("/v1/tools/sos/history/{vehicle_id}")
async def tool_sos_history(vehicle_id: str) -> List[Dict[str, Any]]:
    sos = _get_sos(vehicle_id)
    return sos.get_dispatch_history(vehicle_id)


@app.post("/v1/tools/sos/{vehicle_id}/contacts/add")
async def tool_sos_add_contact(vehicle_id: str, contact: Dict[str, str]) -> Dict[str, Any]:
    sos = _get_sos(vehicle_id)
    sos.add_emergency_contact(vehicle_id, contact)
    return {"status": "added"}


@app.get("/v1/tools/sos/{vehicle_id}/contacts")
async def tool_sos_get_contacts(vehicle_id: str) -> List[Dict[str, str]]:
    sos = _get_sos(vehicle_id)
    return sos.get_emergency_contacts(vehicle_id)


# ============ Speed Detector ============

@app.post("/v1/tools/speed/process")
async def tool_speed_process(body: SpeedReadingRequest) -> Dict[str, Any]:
    sd = _get_speed(body.vehicle_id)
    return sd.process_speed_reading(body.current_speed_kmh, body.speed_limit_kmh, body.timestamp_ms)


@app.get("/v1/tools/speed/{vehicle_id}/status")
async def tool_speed_status(vehicle_id: str) -> Dict[str, Any]:
    sd = _get_speed(vehicle_id)
    return sd.get_status()


@app.post("/v1/tools/speed/{vehicle_id}/reset")
async def tool_speed_reset(vehicle_id: str) -> Dict[str, Any]:
    sd = _get_speed(vehicle_id)
    sd.reset()
    return {"status": "reset"}


@app.get("/v1/status/{vehicle_id}")
async def get_status(vehicle_id: str) -> Dict[str, Any]:
    # Not implemented without a dedicated watsonx status endpoint
    raise HTTPException(status_code=501, detail="Status endpoint not implemented for watsonx backend")


@app.get("/v1/incidents/{vehicle_id}")
async def get_incidents(vehicle_id: str) -> List[Dict[str, Any]]:
    # Not implemented without a remote log store
    raise HTTPException(status_code=501, detail="Incidents endpoint not implemented for watsonx backend")


@app.get("/v1/alerts/{vehicle_id}")
async def get_alerts(vehicle_id: str) -> List[Dict[str, Any]]:
    # Not implemented without a remote log store
    raise HTTPException(status_code=501, detail="Alerts endpoint not implemented for watsonx backend")
