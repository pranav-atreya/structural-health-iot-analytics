"""Telemetry payload validation and InfluxDB point construction.

Validates incoming ESP32 JSON telemetry messages from MQTT:
- Rejects malformed JSON, non-dict payloads, missing `device_id`, and non-finite
  numeric values (NaN, Infinity, -Infinity).
- Strips unsupported legacy fields (`deflection_mm`, ToF fields) with a warning.
- Preserves uncalibrated HX711 counts (`hx711_raw_counts`, `hx711_net_counts`,
  `hx711_filtered_counts`) and NEVER fabricates calibrated grams when `load_grams`
  is null or `hx711_calibrated` is false.
- Adds server-side UTC timestamp and constructs InfluxDB `bridge_telemetry` points.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
import math
from typing import Any, Dict, Optional, Tuple

from influxdb_client import Point, WritePrecision

logger = logging.getLogger(__name__)

MEASUREMENT_NAME = "bridge_telemetry"

FLOAT_FIELDS = (
    "vibration_rms_g",
    "vibration_peak_g",
    "ax_g",
    "ay_g",
    "az_g",
    "gx_dps",
    "gy_dps",
    "gz_dps",
    "hx711_filtered_counts",
    "calibration_factor",
)

OPTIONAL_NULLABLE_FLOAT_FIELDS = (
    "load_grams",
    "last_speed_mps",
)

INT_FIELDS = (
    "seq",
    "uptime_ms",
    "imu_who_am_i",
    "hx711_raw_counts",
    "hx711_net_counts",
    "ir1_state",
    "ir2_state",
    "ir1_events",
    "ir2_events",
    "vehicle_count",
    "last_crossing_ms",
)

BOOL_FIELDS = (
    "imu_ready",
    "hx711_ready",
    "hx711_calibrated",
)

UNSUPPORTED_TOF_FIELDS = (
    "deflection_mm",
    "tof_mm",
    "vl53l0x_mm",
)


class TelemetryValidationError(ValueError):
    """Raised when an MQTT telemetry payload fails structural or numeric validation."""


@dataclass
class ValidatedTelemetry:
    """Normalized representation of a validated ESP32 telemetry packet."""

    device_id: str
    firmware_version: str
    data_source: str
    server_timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    fields: Dict[str, Any] = field(default_factory=dict)
    raw_dict: Dict[str, Any] = field(default_factory=dict)


def _is_finite_number(val: Any) -> bool:
    """Return True if val is an int or float (not bool) and is finite."""
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return False
    return math.isfinite(float(val))


def _parse_finite_float(key: str, val: Any) -> float:
    """Validate and convert a JSON value to a finite float."""
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise TelemetryValidationError(f"Field '{key}' must be numeric, got {type(val).__name__}")
    fval = float(val)
    if not math.isfinite(fval):
        raise TelemetryValidationError(f"Field '{key}' must be finite, got {val}")
    return fval


def _parse_int(key: str, val: Any) -> int:
    """Validate and convert a JSON value to an integer."""
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise TelemetryValidationError(f"Field '{key}' must be integer/numeric, got {type(val).__name__}")
    if isinstance(val, float):
        if not math.isfinite(val) or not val.is_integer():
            raise TelemetryValidationError(f"Field '{key}' must be an exact integer, got {val}")
    return int(val)


def format_imu_chip_tag(who_am_i: Optional[int]) -> str:
    """Format the IMU WHO_AM_I register value honestly without assuming MPU6050."""
    if who_am_i is None:
        return "unknown"
    if who_am_i == 0x68:
        return "0x68_MPU6050"
    if who_am_i == 0x70:
        return "0x70_MPU6500"
    return f"0x{who_am_i:02X}"


def parse_and_validate_payload(
    raw_payload: str | bytes,
    server_timestamp: Optional[datetime] = None,
) -> ValidatedTelemetry:
    """Decode and validate a raw JSON telemetry string/bytes from MQTT."""
    if server_timestamp is None:
        server_timestamp = datetime.now(timezone.utc)
    elif server_timestamp.tzinfo is None:
        server_timestamp = server_timestamp.replace(tzinfo=timezone.utc)

    if isinstance(raw_payload, bytes):
        try:
            text = raw_payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise TelemetryValidationError(f"Invalid UTF-8 bytes in payload: {exc}") from exc
    elif isinstance(raw_payload, str):
        text = raw_payload
    else:
        raise TelemetryValidationError(f"Unsupported payload type: {type(raw_payload).__name__}")

    text = text.strip()
    if not text:
        raise TelemetryValidationError("Empty telemetry payload")

    try:
        # Use parse_constant to immediately reject NaN / Infinity tokens in JSON
        def _reject_non_finite_constant(token: str) -> Any:
            raise TelemetryValidationError(f"Non-finite JSON constant '{token}' is not allowed")

        data = json.loads(text, parse_constant=_reject_non_finite_constant)
    except json.JSONDecodeError as exc:
        raise TelemetryValidationError(f"Malformed JSON payload: {exc}") from exc

    if not isinstance(data, dict):
        raise TelemetryValidationError("Telemetry JSON root must be an object/dictionary")

    # Reject or warn if deprecated VL53L0X/ToF fields are present
    for legacy_key in UNSUPPORTED_TOF_FIELDS:
        if legacy_key in data:
            logger.warning(
                "Stripping unsupported ToF/displacement field '%s' from payload (VL53L0X dropped)",
                legacy_key,
            )
            data.pop(legacy_key, None)

    device_id = data.get("device_id")
    if not isinstance(device_id, str) or not device_id.strip():
        raise TelemetryValidationError("Missing or empty required string field 'device_id'")
    device_id = device_id.strip()

    firmware_version = str(data.get("firmware_version") or "2.0.0").strip()
    data_source = str(data.get("data_source") or "sensor").strip().lower()
    if data_source not in ("sensor", "synthetic", "test"):
        data_source = "sensor"

    fields: Dict[str, Any] = {}

    # Validate integer fields
    for key in INT_FIELDS:
        if key in data and data[key] is not None:
            fields[key] = _parse_int(key, data[key])

    # Validate float fields
    for key in FLOAT_FIELDS:
        if key in data and data[key] is not None:
            fields[key] = _parse_finite_float(key, data[key])

    # Validate boolean status flags (also stored as int 0/1 for easy Grafana graphing)
    for key in BOOL_FIELDS:
        if key in data and data[key] is not None:
            if not isinstance(data[key], bool):
                raise TelemetryValidationError(f"Field '{key}' must be boolean")
            fields[key] = data[key]
            fields[f"{key}_int"] = 1 if data[key] else 0

    # Validate optional nullable float fields (load_grams, last_speed_mps)
    hx_calibrated = data.get("hx711_calibrated")
    for key in OPTIONAL_NULLABLE_FLOAT_FIELDS:
        if key in data and data[key] is not None:
            fval = _parse_finite_float(key, data[key])
            if key == "load_grams" and hx_calibrated is False:
                # Never store calibrated grams if the payload explicitly reports uncalibrated
                logger.warning("Ignoring load_grams because hx711_calibrated is false")
                continue
            fields[key] = fval

    # Range sanity checks on vibration RMS and peak
    if "vibration_rms_g" in fields and fields["vibration_rms_g"] < 0.0:
        raise TelemetryValidationError("vibration_rms_g cannot be negative")
    if "vibration_peak_g" in fields and fields["vibration_peak_g"] < 0.0:
        raise TelemetryValidationError("vibration_peak_g cannot be negative")
    if "ir1_state" in fields and fields["ir1_state"] not in (0, 1):
        raise TelemetryValidationError(f"ir1_state must be 0 or 1, got {fields['ir1_state']}")
    if "ir2_state" in fields and fields["ir2_state"] not in (0, 1):
        raise TelemetryValidationError(f"ir2_state must be 0 or 1, got {fields['ir2_state']}")

    # Ensure at least one actual measurement field exists
    if not fields:
        raise TelemetryValidationError("Telemetry payload contains no valid measurement fields")

    who_am_i_val = fields.get("imu_who_am_i")
    last_direction = str(data.get("last_direction") or "none").strip()
    calibrated_flag = "true" if ("load_grams" in fields and hx_calibrated is not False) else "false"

    tags = {
        "device_id": device_id,
        "firmware_version": firmware_version,
        "imu_chip": format_imu_chip_tag(who_am_i_val),
        "calibrated": calibrated_flag,
        "data_source": data_source,
        "last_direction": last_direction,
    }

    # Also store last_direction as a string field so Grafana tables/stat panels can query it directly
    fields["last_direction_str"] = last_direction

    return ValidatedTelemetry(
        device_id=device_id,
        firmware_version=firmware_version,
        data_source=data_source,
        server_timestamp=server_timestamp,
        tags=tags,
        fields=fields,
        raw_dict=data,
    )


def build_influx_point(telemetry: ValidatedTelemetry) -> Point:
    """Convert a ValidatedTelemetry instance into an InfluxDB Point."""
    point = Point(MEASUREMENT_NAME).time(telemetry.server_timestamp, WritePrecision.MS)
    for tag_key, tag_val in telemetry.tags.items():
        point = point.tag(tag_key, tag_val)
    for field_key, field_val in telemetry.fields.items():
        point = point.field(field_key, field_val)
    return point


def validate_and_build_point(
    raw_payload: str | bytes,
    server_timestamp: Optional[datetime] = None,
) -> Tuple[ValidatedTelemetry, Point]:
    """Convenience helper returning both the ValidatedTelemetry and InfluxDB Point."""
    validated = parse_and_validate_payload(raw_payload, server_timestamp=server_timestamp)
    point = build_influx_point(validated)
    return validated, point
