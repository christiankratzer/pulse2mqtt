# pulse2mqttt

A simple script to poll raw sml data from a tibber pulse, decode and publish over mqtt in json format

For a an analysis of the tibber pulse and bridge please look here

-  https://blog.wyraz.de/allgemein/a-brief-analysis-of-the-tibber-pulse-bridge/

## Prerequisite

- Http access to the tibber bridge needs to be open. See above link on how to accoomplish that.

## Setup

- Create a working directory in `/opt/pulse2mqtt` or similar.
- Create a python3 virtual environment using the `venv.sh` script or the provided `requirements.txt`.
- Copy the sample configuration file and edit to your needs.
- Start in debug mode.
- Use the provided systemd unit file to run when happy with config.

## config.json

The `config.json` provides following settings

```jsonc
{
  "poll": 10,   # frequence to poll the bridge
  "alive": 900, # emit an alive message to the log every alive seconds
  "log": "/var/log/pulse2mqtt/pulse2mqtt.log",  # logfile

  # loglevel
  # WARNING: exceptions only
  # INFO: startup, stop and keepalive messages
  # DEBUG: include deecoded payloads (usefull for discovering obis values your meter supports)
  "loglevel": "INFO",

  "pulse": {
    "url": "http://tibber-bridge/data.json",    # url to poll the tibber bridge
    "node": "1",            # 1 in most cases
    "user": "admin",        # username always admin
    "password": "XXXX-XXXX" # password, check bottom of bridge
  },

  "mqtt": {
    # topic to publish data on
    "topic": "meter/Zuhause/NNNNNNN/SENSOR",

    "client": {
        # parameters for creating mqtt client
        "client_id": "pulse2mqtt"   # mqtt client name
    },

    # optional credentials
    "credentials": {
    } 

    # optional tls config
    "tls": {
    } 

    # broker connection settings
    "broker": {
        "host": "mqtt.host.name",   # mqtt broker hostname
        "port": 1883                # mqtt broker port
     },

    # any static values you want to add to the messages published
     "static": {
        "OBIS_Meter_number": "NNNNNNN"  
     }
  },

  "obis": {
     # mapping of obis data to json output
      "0100010800ff": {
        "name": "OBIS_Total_in",    # name of obis parameter
        "factor": 0.001,            # optional factor to scale data with
        "round": 0                  # optional rounding
      },
      "0100100700ff": {
        "name": "OBIS_Power_curr"
      }
   }
}
```

### Sample data 

```json
{
  "OBIS_Meter_number": "1APA0xxxxxxxxx",
  "OBIS_Power_curr": 2536.571,
  "OBIS_Total_in": 1800,
  "Time": "2023-08-13T07:11:29",
  "transaction_id": "00f460ae"
}
```

### Notes

- The highest frequency to pull would be every second.  The script will deduplicate data based on the decodeded `transaction_id` value in the sml packet

- Recommeded lowest polling frequency is every 10 seconds.

- The bridge occasionally deliveres corrupted sml data possibly due to race conditions between receiving and exposing the data. These are logged on the logfile.

```
pulse2mqtt 2023-06-26 03:43:05,941 INFO Alive
pulse2mqtt 2023-06-26 03:58:14,641 INFO Alive
pulse2mqtt 2023-06-26 04:11:31,802 WARNING {"msg": "Cannot decode SML data", "sml": "1b1b1b1b0101010176050035b83962006200726500000101760101050011e8130b0a014150410100f43f9a726201650011e8100163087b0076050035b83a6200620072650000070177010b0a014150410100f43f9a070100620affff726201650011e8107577070100603201010101010104"}
pulse2mqtt 2023-06-26 04:13:24,392 INFO Alive
pulse2mqtt 2023-06-26 04:28:33,329 INFO Alive
```

- Output in debug mode contains raw and decoded sml data

```
pulse2mqtt 2023-06-24 12:16:44,510 INFO Start
pulse2mqtt 2023-06-24 12:16:44,513 DEBUG Starting new HTTP connection (1): tibber-bridge:80
pulse2mqtt 2023-06-24 12:16:44,727 DEBUG http://tibber-bridge:80 "GET /data.json?node_id=1 HTTP/1.1" 200 256
pulse2mqtt 2023-06-24 12:16:44,728 DEBUG {"sml": "1b1b1b...."}
pulse2mqtt 2023-06-24 12:16:44,731 DEBUG {"transaction_id": "002f2474", "values": [{"name": null, "obis": "010060320101", "obis_code": "1-0:96.50.1*1", "obis_short": "96.50.1", "value": "APA", "unit": null}, {"name": null, "obis": "0100600100ff", "obis_code": "1-0:96.1.0*255", "obis_short": "96.1.0", "value": "0a014150410100f43f9a", "unit": null}, {"name": "Z\u00e4hlerstand Total", "obis": "0100010800ff", "obis_code": "1-0:1.8.0*255", "obis_short": "1.8.0", "value": 349274.212, "unit": "Wh"}, {"name": "Wirkenergie Total", "obis": "0100020800ff", "obis_code": "1-0:2.8.0*255", "obis_short": "2.8.0", "value": 223.21, "unit": "Wh"}, {"name": "aktuelle Wirkleistung", "obis": "0100100700ff", "obis_code": "1-0:16.7.0*255", "obis_short": "16.7.0", "value": 670.138, "unit": "W"}]}
pulse2mqtt 2023-06-24 12:16:44,731 DEBUG {"OBIS_Total_in": 349.0, "OBIS_Power_curr": 670.138, "OBIS_Meter_number": "1APA0xxxxxxxxx", "transaction_id": "002f2474", "Time": "2023-06-24T10:16:44"}
pulse2mqtt 2023-06-24 12:16:53,004 INFO Start
```

- Decoded sml

```json
{
  "transaction_id": "002f2474",
  "values": [
    {
      "name": null,
      "obis": "010060320101",
      "obis_code": "1-0:96.50.1*1",
      "obis_short": "96.50.1",
      "unit": null,
      "value": "APA"
    },
    {
      "name": null,
      "obis": "0100600100ff",
      "obis_code": "1-0:96.1.0*255",
      "obis_short": "96.1.0",
      "unit": null,
      "value": "0a014150410100f43f9a"
    },
    {
      "name": "Zählerstand Total",
      "obis": "0100010800ff",
      "obis_code": "1-0:1.8.0*255",
      "obis_short": "1.8.0",
      "unit": "Wh",
      "value": 349274.212
    },
    {
      "name": "Wirkenergie Total",
      "obis": "0100020800ff",
      "obis_code": "1-0:2.8.0*255",
      "obis_short": "2.8.0",
      "unit": "Wh",
      "value": 223.21
    },
    {
      "name": "aktuelle Wirkleistung",
      "obis": "0100100700ff",
      "obis_code": "1-0:16.7.0*255",
      "obis_short": "16.7.0",
      "unit": "W",
      "value": 670.138
    }
  ]
}
```


