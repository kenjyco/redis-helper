import click


@click.command()
def main():
    """Clear all Collection locks"""
    import redis_helper as rh

    if rh.REDIS is None:
        connected, _ = rh.connect_to_server()
        if not connected:
            raise Exception('Unable to connect to {}'.format(rh.REDIS_URL))
    rh.Collection.clear_all_collection_locks()


if __name__ == '__main__':
    main()
