#include "os.h"
#include "cx.h"
#include "os_io_seproxyhal.h"
#include "algo_tx.h"

#define FETCH_MORE_DATA 1
#define TNX_DECODE_ERROR 2



void parse_input_for_get_public_key_command(const uint8_t* buffer, const uint32_t buffer_len, uint32_t* account_id);
void send_address_to_ui(const uint8_t* public_key, const uint32_t public_key_size);
char* parse_input_for_msgpack_command(const uint8_t * data_buffer, const uint32_t buffer_len, 
                        uint8_t* current_tnx_buffer, const uint32_t current_tnx_buffer_size, uint32_t *current_tnx_buffer_offset,
                        txn_t* current_tnx);
