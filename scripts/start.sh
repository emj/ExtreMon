#!/bin/bash
#-------------------------------------
COMMONRAIL_HOME=`pwd`
#-------------------------------------
export PYTHONPATH=$COMMONRAIL_HOME

# start collectd
screen -dmS commonrail_collectd taskset -c 0   	collectd -f

# start filters
screen -dmS commonrail_label_filter 			filters/label_cleanup_filter.py

# start aggregators
screen -dmS commonrail_df_aggregator			aggregators/df.py

# start missing state contributor
screen -dmS commonrail_missing_states			contributors/missing.py

# start specific contributors
screen -dmS commonrail_http_probes				contributors/httpprobe_state.py
screen -dmS commonrail_xkms2					contributors/trust_state.py
screen -dmS commonrail_trust_list				contributors/tsl_state.py
screen -dmS commonrail_general_state			contributors/state.py

# start subscription servers
screen -dmS commonrail_http_server_sel			servers/http_chalice_server_selective.py 				be.apsu.mon.$HOSTNAME.dispatcher localhost 17817
screen -dmS commonrail_sse_server_sel			servers/sse_chalice_server_selective.py 				be.apsu.mon.$HOSTNAME.dispatcher localhost 17917

# start extremon -> graphite
screen -dmS extremon2graphite 					clients/start_extremon2graphite.sh
