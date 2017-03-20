import redis_helper as rh


sample = rh.Collection(
    'ns',
    'sample',
    unique_field='name',
    index_fields='status',
    json_fields='data',
    insert_ts=True
)
