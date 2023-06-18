import click


@click.command()
def main():
    """Show info about the Collections"""
    import redis_helper as rh

    if rh.REDIS is None:
        connected, _ = rh.connect_to_server()
        if not connected:
            raise Exception('Unable to connect to {}'.format(rh.REDIS_URL))
    rh.Collection.report_all()


if __name__ == '__main__':
    main()
