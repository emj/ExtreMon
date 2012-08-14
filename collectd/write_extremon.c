/**
* ExtreMon Project
* Copyright (C) 2009-2012 Frank Marien
* frank@apsu.be
*
* collectd - src/write_extremon.c
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

#if HAVE_PTHREAD_H
# include <pthread.h>
#endif


/*
 * Private variables
 */


struct we_callback_s
{
  int               socket;
  int               port;
  char*             hostname;
  char*             prefix;

  char              send_buffer[16384];
  size_t            send_buffer_free;
  size_t            send_buffer_fill;
  cdtime_t          send_buffer_init_time;
  struct timeval    last_write;
  pthread_mutex_t   send_lock;
};
typedef struct we_callback_s we_callback_t;


int format_values_extremon (char *ret, size_t ret_len, 
                            const data_set_t *ds, const value_list_t *vl, 
                            _Bool store_rates)
{
  size_t    offset = 0;
  int       status=0;
  int       i;
  gauge_t*  rates = NULL;

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
    if ((vl->plugin_instance==NULL) || (strlen (vl->plugin_instance)= 0))
    {
      if ((vl->type_instance==NULL) || (strlen(vl->type_instance)==0))
        BUFFER_ADD("%s.%s.%s.",vl->host,vl->plugin,vl->type);
      else
        BUFFER_ADD("%s.%s.%s.%s.",vl->host,vl->plugin,vl->type,
                                  vl->type_instance);
    }
    else
    {
      if ((vl->type_instance == NULL) || (strlen(vl->type_instance) == 0))
        BUFFER_ADD("%s.%s.%s.%s.", vl->host,vl->plugin,
                                   vl->plugin_instance, vl->type);
      else
        BUFFER_ADD("%s.%s.%s.%s.%s.", vl->host,vl->plugin,
                                      vl->plugin_instance,vl->type,
                                      vl->type_instance);
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

 
static void we_reset_buffer (we_callback_t *cb)  
{
  memset (cb->send_buffer, 0, sizeof (cb->send_buffer));
  cb->send_buffer_free = sizeof (cb->send_buffer);
  cb->send_buffer_fill = 0;
  cb->send_buffer_init_time = cdtime ();
  gettimeofday(&cb->last_write,NULL);
}

static int we_send_buffer(we_callback_t *cb) 
{
  char values[1024];
  size_t values_len;
  struct timeval time;

  gettimeofday(&time,NULL);
  snprintf(values,sizeof(values)-2,"%s.timestamp=%llu.%llu\n",
                                    cb->prefix,
                                    (unsigned long long)time.tv_sec,
                                    (unsigned long long)time.tv_usec);
  values_len=strlen(values);    

  assert (values_len < cb->send_buffer_free);
  memcpy (cb->send_buffer + cb->send_buffer_fill, values, values_len + 1);
  cb->send_buffer_fill += values_len;
  cb->send_buffer_free -= values_len;

  int bytessent=sendto(cb->socket,cb->send_buffer,cb->send_buffer_fill,
                       0,NULL,0);
  if(bytessent==-1)
  {
    ERROR ("write_extremon plugin: sendto failed");
    return (-1);
  }

  DEBUG("%d bytes sent",bytessent);
  return (0);
}

static int we_set_max_msg_size(we_callback_t *cb, int requested_size)
{
  socklen_t optlen = sizeof(int);
  int optval=requested_size;

  if(setsockopt(cb->socket, SOL_SOCKET, SO_SNDBUF, 
                (int *)&optval, optlen)==-1)
  {
    ERROR ("setting max_msg_size on socket failed");
    return (-1);
  }

  if(getsockopt(cb->socket, SOL_SOCKET, SO_SNDBUF, 
                (int *)&optval, &optlen)==-1)
  {
    ERROR ("verifying max_msg_size on socket failed");
    return (-1);
  }
  
  if(optval!=requested_size)
  {
    ERROR ("setting max_msg_size on socket failed: system limited to %d",
            optval);
    return (1);
  }
  
  return 0;
}

static int we_callback_init(we_callback_t *cb) 
{
  struct sockaddr_in si_other;

  if (cb->socket != -1)
    return (0);

  if((cb->socket=socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP))==-1)
  {
    ERROR ("write_extremon plugin: socket failed.");
    return (-1);
  }

  memset((char *) &si_other, 0, sizeof(si_other));
  si_other.sin_family = AF_INET;
  si_other.sin_port = htons(cb->port);
  if (inet_aton(cb->hostname, &si_other.sin_addr)==0)
  {
    ERROR ("write_extremon plugin: inet_aton failed.");
    return (-1);
  }

  u_char ttl=0;
  if(setsockopt(cb->socket, IPPROTO_IP, IP_MULTICAST_TTL, 
                &ttl, sizeof(ttl))==-1)
  {
    ERROR ("write_extremon plugin: setting multicast scope "
           "to host-only failed.");
    return (-1);
  }

  if(connect(cb->socket, (struct sockaddr *)&si_other,
              sizeof(si_other))==-1)
  {
    ERROR ("write_extremon plugin: connect failed.");
    return (-1);
  }

  we_set_max_msg_size(cb,sizeof(cb->send_buffer));

  we_reset_buffer (cb);
  return (0);
} 

static int we_flush_nolock (cdtime_t timeout, we_callback_t *cb) 
{
  int status;

  DEBUG("write_extremon plugin: we_flush_nolock: timeout = %.3f; "
        "send_buffer_fill = %zu;", CDTIME_T_TO_DOUBLE (timeout),
                                  cb->send_buffer_fill);

  if(timeout>0)
  {
    cdtime_t now;
    now = cdtime ();
    if ((cb->send_buffer_init_time + timeout) > now)
      return (0);
  }

/*  if (cb->send_buffer_fill <= 0)
# {
#   cb->send_buffer_init_time = cdtime ();
#   return (0);
# } */

  status = we_send_buffer (cb);
  we_reset_buffer (cb);

  return (status);
} 

static int we_flush ( cdtime_t timeout,
                      const char *identifier __attribute__((unused)),
                      user_data_t *user_data)
{
  we_callback_t *cb;
  int status;

  if (user_data == NULL)
    return (-EINVAL);

  cb=user_data->data;

  pthread_mutex_lock (&cb->send_lock);

  if (cb->socket == -1)
  {
    status = we_callback_init (cb);
    if (status != 0)
    {
      ERROR ("write_extremon plugin: we_callback_init failed.");
      pthread_mutex_unlock (&cb->send_lock);
      return (-1);
    }
  } 

  status = we_flush_nolock (timeout, cb);
  pthread_mutex_unlock (&cb->send_lock);
  return (status);
} 

static void we_callback_free (void *data) 
{
  we_callback_t *cb;

  if (data == NULL)
    return;

  cb = data;
  we_flush_nolock (0, cb);

  close(cb->socket);
  cb->socket=-1;
  sfree (cb->hostname);
  sfree (cb->prefix);
  sfree (cb);
} 

static int we_write_command (const data_set_t *ds, 
                             const value_list_t *vl, we_callback_t *cb)
{
  char values[1024];
  size_t values_len;
  int status;

  if(0 != strcmp (ds->type, vl->type)) 
  {
    ERROR ("write_extremon plugin: DS type does not match "
           "value list type");
    return -1;
  }

  status = format_values_extremon(values, sizeof (values), ds, vl, 1);
  values_len=strlen(values);
  if (status != 0)
  {
      ERROR ("write_extremon plugin: error with format_values_extremon");
      return (status);
  }

  pthread_mutex_lock (&cb->send_lock);

  if(cb->socket == -1)
  {
    status = we_callback_init (cb);
    if (status != 0)
    {
      ERROR ("write_extremon plugin: we_callback_init failed.");
      pthread_mutex_unlock (&cb->send_lock);
      return (-1);
    }
  } 
  
  if(values_len >= (cb->send_buffer_free-64))
  { 
    DEBUG("write_extremon plugin: writing because buffer full");
    status = we_flush_nolock ( 0, cb);
    if (status != 0)
    {
      pthread_mutex_unlock (&cb->send_lock);
      return (status);
    }
  }

  struct timeval now;
  gettimeofday(&now,NULL);

  if(now.tv_sec>cb->last_write.tv_sec || 
    (now.tv_sec==cb->last_write.tv_sec && now.tv_usec > 
    (cb->last_write.tv_usec + 100000)))
  {
    DEBUG("write_extremon plugin: writing because timeout");
    status = we_flush_nolock ( 0, cb);
    if (status != 0)
    {
      pthread_mutex_unlock (&cb->send_lock);
      return (status);
    }
  }

  assert (values_len < cb->send_buffer_free);

  /* `command_len + 1' because `command_len' does not include the
   * trailing null byte. Neither does `send_buffer_fill'. */

  memcpy (cb->send_buffer + cb->send_buffer_fill, values, values_len + 1);
  cb->send_buffer_fill += values_len;
  cb->send_buffer_free -= values_len;

  DEBUG ("write_extremon plugin: <%s> buffer %zu/%zu (%g%%) \"%s\"", 
                cb->location, cb->send_buffer_fill, 
                sizeof (cb->send_buffer),100.0*
                  ((double)cb->send_buffer_fill)/
                  ((double)sizeof(cb->send_buffer)),
                values);
        
  pthread_mutex_unlock (&cb->send_lock);
  return (0);
} 

static int we_write(const data_set_t *ds, const value_list_t *vl, 
                    user_data_t *user_data)
{
  we_callback_t *cb;
  int status;

  if (user_data == NULL)
    return (-EINVAL);

  cb = user_data->data;
  status = we_write_command (ds, vl, cb);
  return (status);
}
 
static int we_config (oconfig_item_t *ci) 
{
  int i;
  we_callback_t *cb;
  user_data_t user_data;

  cb = malloc (sizeof (*cb));
  if (cb == NULL)
  {
    ERROR ("write_extremon plugin: malloc failed.");
    return (-1);
  }

  memset (cb, 0, sizeof (*cb));
  cb->socket=-1;
  cb->hostname=NULL;
  cb->prefix=NULL;
  cb->port=0;

  pthread_mutex_init (&cb->send_lock,  NULL);

  for(i=0;i<ci->children_num;i++)
  {
    oconfig_item_t *child = ci->children + i;
    if (strcasecmp ("host", child->key) == 0)
      cf_util_get_string(child, &cb->hostname);
    else if (strcasecmp ("port", child->key) == 0)
      cf_util_get_int (child, &cb->port);
    else if (strcasecmp ("prefix", child->key) == 0)
      cf_util_get_string(child, &cb->prefix);
    else
      ERROR ("write_extremon plugin: Invalid configuration option: %s.",
              child->key);
  }

  DEBUG ("write_extremon: Registering listener %s:%d", cb->hostname,
          cb->port);

  memset (&user_data, 0, sizeof (user_data));
  user_data.data = cb;
  user_data.free_func = NULL;
  plugin_register_flush ("write_extremon", we_flush, &user_data);
  user_data.free_func = we_callback_free;
  plugin_register_write ("write_extremon", we_write, &user_data);
  we_callback_init(cb);
  return (0);
} 

void module_register (void) 
{ 
  DEBUG ("write_extremon: Module_Register");
  plugin_register_complex_config ("write_extremon", we_config);
} 


