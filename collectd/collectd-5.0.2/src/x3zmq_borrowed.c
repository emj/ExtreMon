/**
 * collectd - src/zeromq.c
 * Copyright (C) 2005-2010  Florian octo Forster
 * Copyright (C) 2009       Aman Gupta
 * Copyright (C) 2010       Julien Ammous
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
 * Authors:
 *   Florian octo Forster <octo at verplant.org>
 *   Aman Gupta <aman at tmm1.net>
 *   Julien Ammous
 **/

//
// mostly copy/pasted from network.c ...
// this whole file will be dropped as soon as
// it can be replaced by network_buffer library
//

#include <arpa/inet.h>

static value_list_t     send_buffer_vl = VALUE_LIST_STATIC;


/*                      1 1 1 1 1 1 1 1 1 1 2 2 2 2 2 2 2 2 2 2 3 3
 *  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 * +-------+-----------------------+-------------------------------+
 * ! Ver.  !                       ! Length                        !
 * +-------+-----------------------+-------------------------------+
 */
struct part_header_s
{
	uint16_t type;
	uint16_t length;
};
typedef struct part_header_s part_header_t;

// we do not want to crypt here
#undef HAVE_LIBGCRYPT

static int write_part_values (char **ret_buffer, int *ret_buffer_len, const data_set_t *ds, const value_list_t *vl)
{
  char *packet_ptr;
  int packet_len;
  int num_values;

  part_header_t pkg_ph;
  uint16_t      pkg_num_values;
  uint8_t      *pkg_values_types;
  value_t      *pkg_values;

  int offset;
  int i;

  num_values = vl->values_len;
  packet_len = sizeof (part_header_t) + sizeof (uint16_t)
    + (num_values * sizeof (uint8_t))
    + (num_values * sizeof (value_t));

  if (*ret_buffer_len < packet_len)
    return (-1);

  pkg_values_types = (uint8_t *) malloc (num_values * sizeof (uint8_t));
  if (pkg_values_types == NULL)
  {
    ERROR ("network plugin: write_part_values: malloc failed.");
    return (-1);
  }

  pkg_values = (value_t *) malloc (num_values * sizeof (value_t));
  if (pkg_values == NULL)
  {
    free (pkg_values_types);
    ERROR ("network plugin: write_part_values: malloc failed.");
    return (-1);
  }

  pkg_ph.type = htons (TYPE_VALUES);
  pkg_ph.length = htons (packet_len);

  pkg_num_values = htons ((uint16_t) vl->values_len);

  for (i = 0; i < num_values; i++)
  {
    pkg_values_types[i] = (uint8_t) ds->ds[i].type;
    switch (ds->ds[i].type)
    {
      case DS_TYPE_COUNTER:
        pkg_values[i].counter = htonll (vl->values[i].counter);
        break;

      case DS_TYPE_GAUGE:
        pkg_values[i].gauge = htond (vl->values[i].gauge);
        break;

      case DS_TYPE_DERIVE:
        pkg_values[i].derive = htonll (vl->values[i].derive);
        break;

      case DS_TYPE_ABSOLUTE:
        pkg_values[i].absolute = htonll (vl->values[i].absolute);
        break;

      default:
        free (pkg_values_types);
        free (pkg_values);
        ERROR ("network plugin: write_part_values: "
            "Unknown data source type: %i",
            ds->ds[i].type);
        return (-1);
    } /* switch (ds->ds[i].type) */
  } /* for (num_values) */

  /*
   * Use `memcpy' to write everything to the buffer, because the pointer
   * may be unaligned and some architectures, such as SPARC, can't handle
   * that.
   */
  packet_ptr = *ret_buffer;
  offset = 0;
  memcpy (packet_ptr + offset, &pkg_ph, sizeof (pkg_ph));
  offset += sizeof (pkg_ph);
  memcpy (packet_ptr + offset, &pkg_num_values, sizeof (pkg_num_values));
  offset += sizeof (pkg_num_values);
  memcpy (packet_ptr + offset, pkg_values_types, num_values * sizeof (uint8_t));
  offset += num_values * sizeof (uint8_t);
  memcpy (packet_ptr + offset, pkg_values, num_values * sizeof (value_t));
  offset += num_values * sizeof (value_t);

  assert (offset == packet_len);

  *ret_buffer = packet_ptr + packet_len;
  *ret_buffer_len -= packet_len;

  free (pkg_values_types);
  free (pkg_values);

  return (0);
} /* int write_part_values */

static int write_part_number (char **ret_buffer, int *ret_buffer_len,
    int type, uint64_t value)
{
  char *packet_ptr;
  int packet_len;

  part_header_t pkg_head;
  uint64_t pkg_value;
  
  int offset;

  packet_len = sizeof (pkg_head) + sizeof (pkg_value);

  if (*ret_buffer_len < packet_len)
    return (-1);

  pkg_head.type = htons (type);
  pkg_head.length = htons (packet_len);
  pkg_value = htonll (value);

  packet_ptr = *ret_buffer;
  offset = 0;
  memcpy (packet_ptr + offset, &pkg_head, sizeof (pkg_head));
  offset += sizeof (pkg_head);
  memcpy (packet_ptr + offset, &pkg_value, sizeof (pkg_value));
  offset += sizeof (pkg_value);

  assert (offset == packet_len);

  *ret_buffer = packet_ptr + packet_len;
  *ret_buffer_len -= packet_len;

  return (0);
} /* int write_part_number */

static int write_part_string (char **ret_buffer, int *ret_buffer_len,
    int type, const char *str, int str_len)
{
  char *buffer;
  int buffer_len;

  uint16_t pkg_type;
  uint16_t pkg_length;

  int offset;

  buffer_len = 2 * sizeof (uint16_t) + str_len + 1;
  if (*ret_buffer_len < buffer_len)
    return (-1);

  pkg_type = htons (type);
  pkg_length = htons (buffer_len);

  buffer = *ret_buffer;
  offset = 0;
  memcpy (buffer + offset, (void *) &pkg_type, sizeof (pkg_type));
  offset += sizeof (pkg_type);
  memcpy (buffer + offset, (void *) &pkg_length, sizeof (pkg_length));
  offset += sizeof (pkg_length);
  memcpy (buffer + offset, str, str_len);
  offset += str_len;
  memset (buffer + offset, '\0', 1);
  offset += 1;

  assert (offset == buffer_len);

  *ret_buffer = buffer + buffer_len;
  *ret_buffer_len -= buffer_len;

  return (0);
} /* int write_part_string */

static int add_to_buffer (char *buffer, int buffer_size, /* {{{ */
    value_list_t *vl_def,
    const data_set_t *ds, const value_list_t *vl)
{
  char *buffer_orig = buffer;
  
  if (write_part_string (&buffer, &buffer_size, TYPE_HOST, vl->host, strlen (vl->host)) != 0)
    return (-1);
  
  if (write_part_number (&buffer, &buffer_size, TYPE_TIME, (uint64_t) vl->time))
    return (-1);
  
  if (write_part_number (&buffer, &buffer_size, TYPE_INTERVAL, (uint64_t) vl->interval))
    return (-1);
    
  if (write_part_string (&buffer, &buffer_size, TYPE_PLUGIN, vl->plugin, strlen (vl->plugin)) != 0)
    return (-1);
  
  if (write_part_string (&buffer, &buffer_size, TYPE_PLUGIN_INSTANCE, vl->plugin_instance, strlen (vl->plugin_instance)) != 0)
    return (-1);
  
  if (write_part_string (&buffer, &buffer_size, TYPE_TYPE, vl->type, strlen (vl->type)) != 0)
    return (-1);
  
  if (write_part_string (&buffer, &buffer_size, TYPE_TYPE_INSTANCE, vl->type_instance, strlen (vl->type_instance)) != 0)
    return (-1);
  
  if (write_part_values (&buffer, &buffer_size, ds, vl) != 0)
    return (-1);

  return (buffer - buffer_orig);
} /* }}} int add_to_buffer */


