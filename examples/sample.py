import redis_helper as rh


sample = rh.Collection(
    'ns',
    'sample',
    unique_field='name',
    index_fields='status',
    json_fields='data',
    rx_name='\S{4,6}',
    rx_status='(active|inactive|cancelled)',
    rx_aws='[a-z]+\-[0-9a-f]+',
    insert_ts=True
)

uses_sample = rh.Collection(
    'ns',
    'uses_sample',
    index_fields='z',
    rx_thing='\S{4,6}',
    reference_fields='thing--ns:sample'
)
