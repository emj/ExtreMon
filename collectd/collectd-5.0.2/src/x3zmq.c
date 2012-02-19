#include "collectd.h"
#include "common.h" /* auxiliary functions */
#include "plugin.h" /* plugin_register_*, plugin_dispatch_values */
#include "utils_cache.h"
#include "network.h"

#include <pthread.h>
#include <zmq.h>

#define BUFFER_SIZE 32768
#define BUFFER_THRESHOLD 32512
#define LABEL_PARTS_SEPARATOR '.'
#define LABEL_VALUE_SEPARATOR '='
#define MAX_VALUE_SIZE 128

struct x3zmq_socket_s
{
	void *socket;
	int type;
};
typedef struct x3zmq_socket_s x3zmq_socket_t;

struct x3zmq_endpoint_s
{
    char*       endpoint;
    int         socket_type;
    uint64_t    highwatermark;
    void*       socket;
    char*       buffer;
    char*       buffer_write_pos;
    size_t      bufsize;
};
typedef struct x3zmq_endpoint_s x3zmq_endpoint;

static int zmq_threads_num = 1;
static void *zmq_context = NULL;

static int        sending_sockets_num = 0;

// private data
static int thread_running = 1;

static void x3zmq_close_callback(void* voidpoint) 
{
    x3zmq_endpoint* endpoint=(x3zmq_endpoint*)voidpoint;
    if(endpoint->socket!=NULL)
        (void)zmq_close(socket);
    sfree(endpoint);
} 

static void free_data(void *data,void *hint) 
{
    DEBUG("Freeing Buffer %p", data);
    sfree (data);
} 


static void buffer_append_label_part(x3zmq_endpoint* endpoint, const char* data, char separator)
{
    size_t data_len=strlen(data);
    memcpy(endpoint->buffer_write_pos,data,data_len);
    endpoint->buffer_write_pos+=data_len;
    *(endpoint->buffer_write_pos)=separator;
    endpoint->buffer_write_pos++;
}

static void buffer_append_value(x3zmq_endpoint* endpoint, const char* format, ...)
{
    va_list ap;
    va_start(ap,format);
    endpoint->buffer_write_pos+=vsprintf(endpoint->buffer_write_pos,format,ap);
    va_end(ap);
    *(endpoint->buffer_write_pos)='\n';
    endpoint->buffer_write_pos++;
}

static void buffer_reset(x3zmq_endpoint* endpoint)
{
    endpoint->bufsize=BUFFER_SIZE;
    endpoint->buffer=malloc(endpoint->bufsize);
    endpoint->buffer_write_pos=endpoint->buffer;
}

static int write_value(const data_set_t *ds, const value_list_t *vl, user_data_t *user_data)
{
    assert(strcmp(ds->type,vl->type)==0);
    assert(vl->plugin!=NULL);
    assert(vl->type!=NULL);

    x3zmq_endpoint* endpoint=(x3zmq_endpoint*)user_data->data;
    gauge_t*        rates=uc_get_rate(ds,vl);
    size_t          buffer_fill;
    int             i;

    /*
     * We need our 0MQ socket to be created in the same thread that we'll use it from
     * So this is the first clean opportunity to do so
     */

    if(endpoint->socket==NULL)
    {
        DEBUG("Creating 0MQ Socket");
        endpoint->socket=zmq_socket(zmq_context,endpoint->socket_type);
        if(endpoint->socket==NULL)
            ERROR("X3ZMQ plugin: zmq_socket failed: %s", zmq_strerror (errno));

        DEBUG("Connecting 0MQ Socket To %s",endpoint->endpoint);
        if(zmq_connect(endpoint->socket,endpoint->endpoint)!=0)
            ERROR("X3ZMQ plugin: zmq_connect (\"%s\") failed: %s", endpoint->endpoint, zmq_strerror (errno));
           
        if(zmq_setsockopt(endpoint->socket,ZMQ_HWM,&endpoint->highwatermark,sizeof(endpoint->highwatermark))!=0)
            ERROR("X3ZMQ plugin: zmq_setsockopt (ZMQ_HWM) failed: %s", zmq_strerror (errno));
     }

    /*
     * For each measure
     */

    for(i=0;i<ds->ds_num;i++)
    {
        /*
         * Add ExtreMon Label: host.plugin[.plugin_instance].type[.type_instance].name=
         */

        buffer_fill=(size_t)(endpoint->buffer_write_pos-endpoint->buffer);
        DEBUG("Adding Label`[%s.%s.%s.%s] buffer at %ld",vl->host,vl->plugin,vl->type,ds->ds[i].name,buffer_fill);
        buffer_append_label_part(endpoint,          vl->host,               LABEL_PARTS_SEPARATOR);
        buffer_append_label_part(endpoint,          vl->plugin,             LABEL_PARTS_SEPARATOR);

        if((vl->plugin_instance!=NULL) && (strlen(vl->plugin_instance)!=0))
            buffer_append_label_part(endpoint,      vl->plugin_instance,    LABEL_PARTS_SEPARATOR);

        buffer_append_label_part(endpoint,          vl->type,               LABEL_PARTS_SEPARATOR);

        if((vl->type_instance!=NULL) && (strlen(vl->type_instance)!=0))
            buffer_append_label_part(endpoint,      vl->type_instance,      LABEL_PARTS_SEPARATOR);

        buffer_append_label_part(endpoint,          ds->ds[i].name,         LABEL_VALUE_SEPARATOR);
            
        /*
         * Add Value
         */

        buffer_fill=(size_t)(endpoint->buffer_write_pos-endpoint->buffer);
        if (ds->ds[i].type==DS_TYPE_GAUGE)
        {
            DEBUG("Adding GAUGE value [%s.%s.%s.%s] buffer at %ld",vl->host,vl->plugin,vl->type,ds->ds[i].name,buffer_fill);
            buffer_append_value(endpoint,"%f",vl->values[i].gauge);
        }
        else if (ds->ds[i].type==DS_TYPE_COUNTER)
        {
            DEBUG("Adding COUNTER value [%s.%s.%s.%s] buffer at %ld",vl->host,vl->plugin,vl->type,ds->ds[i].name,buffer_fill);
            buffer_append_value(endpoint,"%llu",vl->values[i].counter);
        }
        else if(ds->ds[i].type==DS_TYPE_DERIVE)
        {
            DEBUG("Adding DERIVE value [%s.%s.%s.%s] buffer at %ld",vl->host,vl->plugin,vl->type,ds->ds[i].name,buffer_fill);
            if(rates!=NULL)
                buffer_append_value(endpoint,"%g",rates[i]);
            else
            {
                WARNING("DERIVE value from [%s.%s.%s.%s] with no rates available",vl->host,vl->plugin,vl->type,ds->ds[i].name);
                buffer_append_value(endpoint,"0");
            }
        }

        /* 
         * If we're running out of buffer space, hand this buffer over to 0MQ and allocate a new one
         */
        size_t buffer_fill=(size_t)(endpoint->buffer_write_pos-endpoint->buffer);
        if(buffer_fill>=BUFFER_THRESHOLD)
        {
            zmq_msg_t shuttle;

            if(zmq_msg_init_data(&shuttle,endpoint->buffer,buffer_fill,free_data,NULL)!=0)
            {
                ERROR("X3ZMQ: zmq_msg_init : %s", zmq_strerror(errno));
            }
            
            if(zmq_send(endpoint->socket,&shuttle,ZMQ_NOBLOCK)!=0)
            {
                if(errno==EAGAIN)
                {
                    WARNING("X3ZMQ: Unable to queue message, queue may be full");
                }
                else
                {
                    ERROR("X3ZMQ: zmq_send : %s", zmq_strerror(errno));
                }
            }

            buffer_reset(endpoint);
        }
    }

    sfree(rates);
    return 0;
} 

static int x3zmq_config_mode (oconfig_item_t *ci) 
{
  char buffer[64] = "";
  int status;

  status = cf_util_get_string_buffer (ci, buffer, sizeof (buffer));
  if (status != 0)
    return (-1);

  if (strcasecmp ("Publish", buffer) == 0)
    return (ZMQ_PUB);
  else if (strcasecmp ("Push", buffer) == 0)
    return (ZMQ_PUSH);
  
  ERROR ("X3ZMQ plugin: Unrecognized communication pattern: \"%s\"", buffer);
  return (-1);
}



static int x3zmq_config_socket (oconfig_item_t *ci) 
{
    int             i;
    char            name[32];
    user_data_t     user_data={NULL,NULL};

    user_data.data=malloc(sizeof(x3zmq_endpoint));
    if(user_data.data==NULL)
    {
        ERROR ("X3ZMQ plugin: malloc (of endpoint structure) failed.");
        return (-1);
    }

    x3zmq_endpoint* endpoint=(x3zmq_endpoint*)user_data.data;
    endpoint->socket_type=x3zmq_config_mode(ci);
    if(endpoint->socket_type<0)
        return (-1);

    for(i=0;i<ci->children_num;i++)
    {
        oconfig_item_t *child = ci->children + i;
        if(strcasecmp ("Endpoint", child->key) == 0)
        {
            char *value = NULL;
            if(cf_util_get_string(child,&value)==0)
                endpoint->endpoint=strdup(value);
            sfree(value);
        }
        else if( strcasecmp("HighWaterMark", child->key) == 0 )
        {
            int tmp;
            if(cf_util_get_int(child,&tmp)==0)
                endpoint->highwatermark=(uint64_t)tmp;
        }
        else
        {
            ERROR ("X3ZMQ plugin: The \"%s\" config option is now allowed here.", child->key);
        }
    }

    endpoint->socket=NULL;
    buffer_reset(endpoint);
    user_data.free_func=x3zmq_close_callback;
    ssnprintf(name,sizeof(name),"x3zmq/%i",sending_sockets_num);
    sending_sockets_num++;
    plugin_register_write(name,write_value,&user_data);

    return (0);
} 

/*
 * Config schema:
 *
 * <Plugin "x3zmq">
 *   Threads 1
 *
 *   <Socket Publish>
 *     HighWaterMark 300
 *     Endpoint "tcp://localhost:6666"
 *   </Socket>
 *   <Socket Push>
 *     HighWaterMark 300
 *     Endpoint "tcp://localhost:6667"
 *   </Socket>
 * </Plugin>
 */

static int x3zmq_config (oconfig_item_t *ci) /* {{{ */
{
    int status;
    int i;
  
    for (i = 0; i < ci->children_num; i++)
    {
        oconfig_item_t *child = ci->children + i;
        if (strcasecmp ("Socket", child->key) == 0)
        {
            status = x3zmq_config_socket (child);
        }
        else if (strcasecmp ("Threads", child->key) == 0)
        {
            int tmp = 0;
            status=cf_util_get_int (child, &tmp);
            if((status==0) && (tmp>=1))
            {
                zmq_threads_num=tmp;
                if(zmq_context==NULL)
                {
                    zmq_context=zmq_init (zmq_threads_num);
                    if (zmq_context==NULL)
                    {
                        ERROR ("X3ZMQ plugin: Initializing zeromq failed: %s",
                        zmq_strerror(errno));
                        return (-1);
                    }
                    INFO("X3ZMQ: Using %d threads", zmq_threads_num);
                }
            }
        }
        else
        {
            WARNING ("X3ZMQ plugin: The \"%s\" config option is not allowed here.", child->key);
        }
    }     

    return (0);
} 

static int plugin_init (void)
{
  int major, minor, patch;
  zmq_version (&major, &minor, &patch);
  INFO("X3ZMQ plugin loaded (zeromq v%d.%d.%d).", major, minor, patch);
  return 0;
}

static int my_shutdown (void)
{
  if( zmq_context )
  {
    thread_running = 0;
    DEBUG("X3ZMQ: shutting down");
    if(zmq_term(zmq_context) != 0 )
    {
      ERROR("X3ZMQ: zmq_term : %s", zmq_strerror(errno));
      return 1;
    }
  }
  
  return 0;
}

void module_register (void)
{
  plugin_register_complex_config("x3zmq", x3zmq_config);
  plugin_register_init("x3zmq", plugin_init);
  plugin_register_shutdown ("x3zmq", my_shutdown);
}

