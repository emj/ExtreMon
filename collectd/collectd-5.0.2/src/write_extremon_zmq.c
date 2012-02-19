/**
* ExtreMon Project
* Copyright (C) 2009-2012 Frank Marien
* frank@apsu.be
*
* collectd - src/write_extremon_zmq.c
* Based on write_http by Sadauskas,MacEachern & Forster
*
* This file is part of ExtreMon. All other parts of ExtreMon are licenced under
* the GPL, version 3. I had to keep this file at version 2, due to this limitation
* being present in write_http at time of writing - Frank Marien
*
* This program is free software; you can redistribute it and/or modify it
* under the terms of the GNU General Public License as published by the
* Free Software Foundation; only version 2 of the License is applicable.
*
* This program is distributed in the hope that it will be useful, but
* WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
* General Public License for more details.
*
* You should have received a copy of the GNU General Public License along
* with this program; if not, write to the Free Software Foundation, Inc.,
* 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
*
* Authors
*   Florian octo Forster <octo at verplant.org>
*   Doug MacEachern <dougm@hyperic.com>
*   Paul Sadauskas <psadauskas@gmail.com>
*   Frank Marien <frank at apsu.be> - extremon-specific adaptations
**/

#include "collectd.h"
#include "plugin.h"
#include "common.h"
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/types.h>
#include <unistd.h>
#include "utils_cache.h"
#include "utils_parse_option.h"
#include "configfile.h"
#include <zmq.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#if HAVE_PTHREAD_H
# include <pthread.h>
#endif

#define BUFFER_SIZE	32768
#define	FLUSH_NOW 0


/*
 * Private variables
 */


struct we_callback_s
{
	void*				context;
	void*				socket;
	char*				hostname;
	char* 		 		prefix;

    char*   			send_buffer;
    size_t 				send_buffer_free;
    size_t 				send_buffer_fill;
    cdtime_t 			send_buffer_init_time;
    pthread_mutex_t 	buffer_lock;
	struct timeval 		last_write;
	int 				active_buffer;
};
typedef struct we_callback_s we_callback_t;


int format_values_extremon (char *ret, size_t ret_len, const data_set_t *ds, const value_list_t *vl, _Bool store_rates)
{
        size_t offset = 0;
        int status=0;
        int i;
        gauge_t *rates = NULL;

        assert (0 == strcmp (ds->type, vl->type));
	assert (vl->plugin != NULL);
        assert (vl->type != NULL);
        memset (ret, 0, ret_len);

#define BUFFER_ADD(...) do { \
        status = ssnprintf (ret + offset, ret_len - offset, \
                        __VA_ARGS__); \
        if (status < 1) \
        { \
                sfree (rates); \
                return (-1); \
        } \
        else if (((size_t) status) >= (ret_len - offset)) \
        { \
                sfree (rates); \
                return (-1); \
        } \
        else \
                offset += ((size_t) status); \
} while (0)

        for(i=0;i<ds->ds_num;i++)
        {
		if ((vl->plugin_instance == NULL) || (strlen (vl->plugin_instance) == 0))
		{
			if ((vl->type_instance == NULL) || (strlen(vl->type_instance) == 0))
				BUFFER_ADD("%s.%s.%s.", vl->host, vl->plugin, vl->type);
			else
				BUFFER_ADD("%s.%s.%s.%s.", vl->host, vl->plugin, vl->type, vl->type_instance);
		}
		else
		{
			if ((vl->type_instance == NULL) || (strlen(vl->type_instance) == 0))
				BUFFER_ADD("%s.%s.%s.%s.", vl->host, vl->plugin, vl->plugin_instance, vl->type);
			else
				BUFFER_ADD("%s.%s.%s.%s.%s.", vl->host, vl->plugin, vl->plugin_instance, vl->type, vl->type_instance);
		}

                if (ds->ds[i].type==DS_TYPE_GAUGE)
                        BUFFER_ADD ("%s=%f\n", ds->ds[i].name,vl->values[i].gauge);
                else if(store_rates)
                {
                        if(rates==NULL)
                                rates=uc_get_rate (ds, vl);

                        if(rates==NULL)
                        {
                                WARNING ("format_values_extremon : uc_get_rate failed.");
                                return (-1);
                        }

                        BUFFER_ADD ("%s=%g\n", ds->ds[i].name,rates[i]);
                }
                else if (ds->ds[i].type==DS_TYPE_COUNTER)
                        BUFFER_ADD ("%s=%llu\n", ds->ds[i].name,vl->values[i].counter);
	}


#undef BUFFER_ADD

        sfree (rates);
        return (0);
}


static void _we_reset_buffer(we_callback_t* cb)
{
	cb->send_buffer=malloc(BUFFER_SIZE);
	memset (cb->send_buffer, 0, BUFFER_SIZE);
	cb->send_buffer_free = BUFFER_SIZE;
	cb->send_buffer_fill = 0;
	cb->send_buffer_init_time=cdtime ();
	gettimeofday(&cb->last_write,NULL);
}

 
static void we_zmq_done(void* data, void* user_data)
{
	DEBUG("extremon freeing buffer [%p]",data);
	free(data);
}

static int we_send_buffer(we_callback_t *cb) 
{
	char values[1024];
	size_t values_len;
	struct timeval time;
	zmq_msg_t message;

	DEBUG("extremon send buffer [%p]",cb->send_buffer);

	pthread_mutex_lock(&cb->buffer_lock);

	gettimeofday(&time,NULL);
	snprintf(values,sizeof(values)-2,"%s.timestamp=%llu.%llu\n",cb->prefix,(unsigned long long)time.tv_sec,(unsigned long long)time.tv_usec);
	values_len=strlen(values);		

	assert (values_len < cb->send_buffer_free);
	memcpy (cb->send_buffer+cb->send_buffer_fill,values,values_len+1);
	cb->send_buffer_fill += values_len;
	cb->send_buffer_free -= values_len;

	DEBUG("extremon msg_init");
	zmq_msg_init_data(&message,cb->send_buffer, cb->send_buffer_fill,we_zmq_done,cb);

	DEBUG("extremon reset buffer");
	_we_reset_buffer(cb);

	DEBUG("extremon msg_send");
	if(zmq_send(cb->socket,&message,0)==-1)
	{
		ERROR ("write_extremon_zmq plugin: 0MQ Send failed.");
		return(-1);
	}

	DEBUG("extremon msg_close");
    zmq_msg_close(&message);
	
	pthread_mutex_unlock(&cb->buffer_lock);
	
    return (0);
}


static int we_callback_init(we_callback_t *cb) 
{
	DEBUG("init");
    if(cb->socket!=NULL)
		return 0;

	cb->context=zmq_init(1);
	if(cb->context==NULL)
	{
		ERROR ("write_extremon_zmq plugin: 0MQ Initialisation failed.");
		return (-1);
	}

	cb->socket=zmq_socket(cb->context,ZMQ_PUSH);
	if(cb->socket==NULL)
	{
                ERROR ("write_extremon_zmq plugin: 0MQ Push Socket failed.");
                return (-1);
	}

	if(zmq_bind(cb->socket,"tcp://127.0.0.1:2001")==-1)
	{
                ERROR ("write_extremon_zmq plugin: 0MQ Binding Push Socket failed.");
                return (-1);
	}
	
    _we_reset_buffer(cb);
    return(0);
} 

static int _we_flush(cdtime_t timeout, we_callback_t* cb) 
{
	DEBUG("write_extremon_zmq plugin: _we_flush: timeout = %.3f; send_buffer_fill = %zu;", CDTIME_T_TO_DOUBLE (timeout), cb->send_buffer_fill);
	if(timeout>FLUSH_NOW && (((cb->send_buffer_init_time+timeout)>cdtime())))
		return(0);
	return we_send_buffer(cb);
} 

static int we_flush(cdtime_t timeout, const char *identifier __attribute__((unused)), user_data_t *user_data)
{
	we_callback_t* cb;

	if(user_data==NULL)
		return (-EINVAL);
	cb=user_data->data;
	if(cb->socket==NULL)
		return(-EINVAL);
	return _we_flush(timeout,cb);
} 

static void we_callback_free(void *data) 
{
	we_callback_t *cb;

	if(data==NULL)
		return;
	cb=data;
	_we_flush(0,cb);

	zmq_term(cb->context);
	cb->socket=NULL;
	sfree(cb->hostname);
	sfree(cb->prefix);
    sfree(cb);
} 


static int we_write(const data_set_t *ds, const value_list_t *vl, user_data_t *user_data)
{
	we_callback_t *cb;
	char values[1024];
	size_t values_len;
	int status;

	if(user_data==NULL)
		return(-EINVAL);

	cb=user_data->data;
	if(cb->socket == NULL)
		return(-EINVAL);

	if(strcmp(ds->type, vl->type)!=0) 
	{
		ERROR ("write_extremon_zmq plugin: DS type does not match value list type");
		return(-EINVAL);
	}

	status=format_values_extremon(values,sizeof(values),ds,vl,1);
	if(status!=0)
	{
		ERROR ("write_extremon_zmq plugin: error with format_values_extremon");
		return (status);
	}

	values_len=strlen(values);
	if(values_len>=(cb->send_buffer_free-64))
	{
		DEBUG("write_extremon_zmq plugin: writing because buffer full");
		status = _we_flush(FLUSH_NOW,cb);
		if(status!=0)
            return (status);
    }

	struct timeval now;
	gettimeofday(&now,NULL);
	if(now.tv_sec>cb->last_write.tv_sec || (now.tv_sec==cb->last_write.tv_sec && now.tv_usec > (cb->last_write.tv_usec + 100000)))
	{
		DEBUG("write_extremon_zmq plugin: writing because timeout");
		status=_we_flush(FLUSH_NOW,cb);
		if(status!=0)
			return (status);
	}

	assert(values_len<cb->send_buffer_free);

	/* `command_len + 1' because `command_len' does not include the
	 * trailing null byte. Neither does `send_buffer_fill'. */

	memcpy(cb->send_buffer+ cb->send_buffer_fill, values, values_len + 1);
	cb->send_buffer_fill += values_len;
	cb->send_buffer_free -= values_len;

	DEBUG ("write_extremon_zmq plugin: <%s> buffer %zu/%d (%g%%) \"%s\"", cb->hostname, cb->send_buffer_fill, BUFFER_SIZE, 100.0 * ((double) cb->send_buffer_fill) / ((double) BUFFER_SIZE), values);
        
	return (0);
} 

 
static int we_config (oconfig_item_t *ci) 
{
	int i;
        we_callback_t *cb;
        user_data_t user_data;

        cb = malloc (sizeof (*cb));
        if (cb == NULL)
        {
                ERROR ("write_extremon_zmq plugin: malloc failed.");
                return (-1);
        }

        memset (cb, 0, sizeof (*cb));
	cb->context=NULL;
	cb->socket=NULL;
	cb->hostname=NULL;
	cb->prefix=NULL;

   pthread_mutex_init(&cb->buffer_lock,NULL);

	for(i=0;i<ci->children_num;i++)
	{
		oconfig_item_t *child = ci->children + i;
                if (strcasecmp ("host", child->key) == 0)
			cf_util_get_string(child, &cb->hostname);
                else if (strcasecmp ("prefix", child->key) == 0)
			cf_util_get_string(child, &cb->prefix);
		else
			ERROR ("write_extremon_zmq plugin: Invalid configuration option: %s.", child->key);
	}

        DEBUG ("write_extremon_zmq: Registering listener %s", cb->hostname);

        memset (&user_data, 0, sizeof (user_data));
        user_data.data = cb;
        user_data.free_func = NULL;
        plugin_register_flush ("write_extremon_zmq", we_flush, &user_data);

        user_data.free_func = we_callback_free;
        plugin_register_write ("write_extremon_zmq", we_write, &user_data);

	we_callback_init(cb);

	return (0);
} 

void module_register (void) 
{	
    DEBUG ("write_extremon_zmq: Module_Register");
	plugin_register_complex_config ("write_extremon_zmq", we_config);
} 


