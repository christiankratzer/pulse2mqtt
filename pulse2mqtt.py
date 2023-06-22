#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set expandtab sw=4 ts=4:

from smllib import SmlStreamReader
from smllib.const import OBIS_NAMES, UNITS
import paho.mqtt.client as mqtt
import datetime
import logging
import traceback
import requests
import copy
import time
import math
import json
import sys
import os

# read config
if len(sys.argv)>1:
    config_path = sys.argv[1]
else:
    config_path = 'config.json'

with open(config_path, 'r') as f:
    config = json.loads(f.read())

# setup logging
logging.basicConfig(
    filename=config["log"],
    format='api %(asctime)s %(levelname)s %(message)s',
    level=getattr(logging, config.get("loglevel","INFO")))

# setup requests session
session = requests.Session()


# setup mqtt client
if 'mqtt' in sys.argv:
    client = mqtt.Client( **config["mqtt"]["client"] )

    if 'tls' in config["mqtt"]:
        client.tls_set(**config["mqtt"]["tls"])

    if 'credentials' in config["mqtt"]:
        client.username_pw_set( **config["mqtt"]["credentials"] )

    client.connect( **config["mqtt"]["broker"] )
else:
    client = None


def poll( config, session ):
    pulse_url  = config['pulse']['url']
    pulse_auth = ( config['pulse']['user'], config['pulse']['password'] )
    pulse_params = { 'node_id': config['pulse']['node'] }

    r = session.get( pulse_url, auth=pulse_auth, params=pulse_params )
    if r.status_code==200:
        smldata = r.content
        if len(smldata)>0:
           return smldata

    return None


def decode_sml( config, smldata ):
    stream = SmlStreamReader()
    stream.add(smldata)
    sml_frame = stream.get_frame()

    parsed_msgs = sml_frame.parse_frame()
    msg = parsed_msgs[1]
    values = []

    # Shortcut to extract all values without parsing the whole frame
    obis_values = sml_frame.get_obis()
    for list_entry in obis_values:
        obis = {
            'name': OBIS_NAMES.get( list_entry.obis ),
            'obis': list_entry.obis,
            'obis_code': list_entry.obis.obis_code,
            'obis_short': list_entry.obis.obis_short,
        }
        if list_entry.value:
            if list_entry.scaler:
                obis['value'] = list_entry.value * math.pow(10,int(list_entry.scaler))
            else:
                obis['value'] = list_entry.value
            obis['unit'] = UNITS.get( list_entry.unit )

        values.append(obis)

    return msg.transaction_id, values


def map_values_to_msg( config, values_in ):
   msg = {}
   for v in values_in:
        obis = v['obis']
        if obis in config['obis']:
           name = config['obis'][obis]['name']
           value = v['value']

           transform_factor = config['obis'][obis].get('factor')
           if transform_factor:
                value = value * transform_factor

           transform_round = config['obis'][obis].get('round')
           if transform_round is not None:
                value = round(value, transform_round)

           msg[name] = value

   msg.update(config['mqtt']['static'])

   return msg


def run( config, tid_old, session, client ):
    # poll raw sml data
    smldata = poll(config, session)
    if not smldata:
        return tid_old

    # decode transaction_id and values
    tid_new, values = decode_sml(config, smldata)
    if tid_new==tid_old:
        return tid_old

    # map sml to mqtt msg
    msg = map_values_to_msg(config, values)
    msg['transaction_id'] = tid_new
    msg['Time'] = datetime.datetime.utcnow().isoformat()[:19]

    # publish or print
    if client:
        client.publish(config['mqtt']['topic'],json.dumps(msg))
        logging.debug(json.dumps(msg))
    else:
        print(json.dumps(msg))

    return tid_new


# main loop
logging.info('Start')
t0 = time.time()

if client:
    client.loop_start()
try:
    tid = None
    while True:
        tid = run( config, tid, session, client )
        time.sleep( config['poll'] )

        t1 = time.time()
        if t1-t0>config.get('alive',300):
            logging.info('Alive')
            t0=t1

except Exception as e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    ex = {
        'exception':str(e),
        'traceback': traceback.format_exc().split('\n'),
        'file': os.path.split(exc_tb.tb_frame.f_code.co_filename)[1],
        'line': exc_tb.tb_lineno,
        }
    logging.warning(json.dumps(ex))

finally:
    if client:
        client.loop_stop()
        client.disconnect()

    logging.info('Stop')




