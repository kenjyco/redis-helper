import click
from pprint import pprint


@click.command()
def main():
    """Interactively select a Collection model and start ipython shell"""
    import redis_helper as rh
    import input_helper as ih

    if rh.REDIS is None:
        connected, _ = rh.connect_to_server()
        if not connected:
            raise Exception('Unable to connect to {}'.format(rh.REDIS_URL))
    selected = rh.Collection.select_models(named=True)
    if selected:
        ih.start_ipython(warn=True, rh=rh, ih=ih, **selected)


if __name__ == '__main__':
    main()
