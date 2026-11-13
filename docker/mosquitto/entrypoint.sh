#!/bin/sh
set -e

CONF_RUNTIME="/tmp/mosquitto_runtime.conf"
PASSWD_FILE="/tmp/mosquitto.passwd"

cp /mosquitto/config/mosquitto.conf "$CONF_RUNTIME"

if [ "${MQTT_ALLOW_ANONYMOUS}" = "true" ]; then
    echo "[mosquitto-init] Anonymous lab access enabled"
    echo "allow_anonymous true" >> "$CONF_RUNTIME"
else
    MQTT_USER="${MQTT_USERNAME:-bridge_iot}"
    MQTT_PASS="${MQTT_PASSWORD:-bridge_iot_pass}"

    touch "$PASSWD_FILE"
    mosquitto_passwd -b "$PASSWD_FILE" "$MQTT_USER" "$MQTT_PASS"

    chown mosquitto:mosquitto "$PASSWD_FILE"
    chmod 0600 "$PASSWD_FILE"

    echo "allow_anonymous false" >> "$CONF_RUNTIME"
    echo "password_file $PASSWD_FILE" >> "$CONF_RUNTIME"
    echo "[mosquitto-init] Configured authenticated MQTT broker for user: $MQTT_USER"
fi

exec /usr/sbin/mosquitto -c "$CONF_RUNTIME"
