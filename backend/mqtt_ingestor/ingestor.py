"""Resilient MQTT-to-InfluxDB ingestion service for Structural Health IoT Analytics."""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
from typing import Any

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
import paho.mqtt.client as mqtt

from backend.mqtt_ingestor.validator import (
    TelemetryValidationError,
    validate_and_build_point,
)

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mqtt_ingestor")


class MqttToInfluxIngestor:
    """Subscribes to ESP32 MQTT telemetry and writes validated points to InfluxDB 2.x."""

    def __init__(self) -> None:
        self.mqtt_host = os.getenv("MQTT_BROKER_HOST", "localhost")
        self.mqtt_port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
        self.mqtt_username = os.getenv("MQTT_USERNAME", "bridge_iot")
        self.mqtt_password = os.getenv("MQTT_PASSWORD", "bridge_iot_pass")
        self.mqtt_topic = os.getenv("MQTT_TOPIC", "structural-health/+/telemetry")

        self.influx_url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
        self.influx_token = os.getenv(
            "INFLUXDB_TOKEN", "structural-health-iot-local-dev-token-2026"
        )
        self.influx_org = os.getenv("INFLUXDB_ORG", "pes-iot")
        self.influx_bucket = os.getenv("INFLUXDB_BUCKET", "structural_health")

        self.running = True
        self.messages_received = 0
        self.messages_written = 0
        self.messages_rejected = 0

        self.influx_client = InfluxDBClient(
            url=self.influx_url,
            token=self.influx_token,
            org=self.influx_org,
            timeout=10_000,
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)

        self.mqtt_client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"structural-health-ingestor-{os.getpid()}",
        )
        if self.mqtt_username:
            self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)

        self.mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_disconnect = self._on_disconnect
        self.mqtt_client.on_message = self._on_message

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Any,
        reason_code: Any,
        properties: Any = None,
    ) -> None:
        if reason_code == 0:
            logger.info(
                "Connected to MQTT broker %s:%d — subscribing to '%s'",
                self.mqtt_host,
                self.mqtt_port,
                self.mqtt_topic,
            )
            client.subscribe(self.mqtt_topic, qos=0)
        else:
            logger.error("MQTT connection failed with reason_code=%s", reason_code)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: Any,
        reason_code: Any,
        properties: Any = None,
    ) -> None:
        if self.running:
            logger.warning(
                "Disconnected from MQTT broker (reason=%s). Paho will auto-reconnect...",
                reason_code,
            )

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        msg: mqtt.MQTTMessage,
    ) -> None:
        self.messages_received += 1
        try:
            validated, point = validate_and_build_point(msg.payload)
        except TelemetryValidationError as exc:
            self.messages_rejected += 1
            logger.warning(
                "Rejected invalid message on topic '%s' (#%d rejected): %s",
                msg.topic,
                self.messages_rejected,
                exc,
            )
            return
        except Exception as exc:  # pragma: no cover
            self.messages_rejected += 1
            logger.exception("Unexpected error parsing message on '%s': %s", msg.topic, exc)
            return

        try:
            self.write_api.write(
                bucket=self.influx_bucket,
                org=self.influx_org,
                record=point,
            )
            self.messages_written += 1
            if self.messages_written == 1 or self.messages_written % 10 == 0:
                logger.info(
                    "Wrote point #%d | device=%s seq=%s rms_g=%.4f hx_filt=%s veh=%s src=%s",
                    self.messages_written,
                    validated.device_id,
                    validated.fields.get("seq", "-"),
                    validated.fields.get("vibration_rms_g", 0.0),
                    validated.fields.get("hx711_filtered_counts", "-"),
                    validated.fields.get("vehicle_count", "-"),
                    validated.data_source,
                )
        except Exception as exc:
            logger.error(
                "Failed writing point to InfluxDB (%s, bucket=%s): %s",
                self.influx_url,
                self.influx_bucket,
                exc,
            )

    def wait_for_influxdb(self, max_wait_sec: int = 60) -> None:
        """Wait until InfluxDB health endpoint reports ready before starting ingestion."""
        deadline = time.time() + max_wait_sec
        while self.running and time.time() < deadline:
            try:
                if self.influx_client.ping():
                    logger.info(
                        "InfluxDB is reachable at %s (org=%s, bucket=%s)",
                        self.influx_url,
                        self.influx_org,
                        self.influx_bucket,
                    )
                    return
            except Exception as exc:
                logger.debug("Waiting for InfluxDB: %s", exc)
            logger.info("Waiting for InfluxDB at %s to become ready...", self.influx_url)
            time.sleep(2)
        logger.warning(
            "Proceeding even though InfluxDB ping did not succeed within %ds", max_wait_sec
        )

    def run(self) -> None:
        """Main blocking service loop with graceful shutdown handling."""
        def _handle_signal(signum: int, frame: Any) -> None:
            logger.info("Received signal %d — shutting down ingestor...", signum)
            self.running = False
            try:
                self.mqtt_client.disconnect()
            except Exception:
                pass

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        self.wait_for_influxdb(max_wait_sec=45)

        while self.running:
            try:
                logger.info(
                    "Connecting to MQTT broker at %s:%d...", self.mqtt_host, self.mqtt_port
                )
                self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, keepalive=30)
                self.mqtt_client.loop_forever(retry_first_connection=True)
            except Exception as exc:
                if not self.running:
                    break
                logger.warning(
                    "MQTT connection loop interrupted (%s). Retrying in 5 seconds...", exc
                )
                time.sleep(5)

        try:
            self.write_api.close()
            self.influx_client.close()
        except Exception:
            pass
        logger.info(
            "Ingestor stopped cleanly (received=%d, written=%d, rejected=%d)",
            self.messages_received,
            self.messages_written,
            self.messages_rejected,
        )


def main() -> int:
    ingestor = MqttToInfluxIngestor()
    ingestor.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
