import click


@click.command()
def main():
    """Interactively select a Collection model and start ipython shell"""
    from IPython import embed
    import redis_helper as rh
    import input_helper as ih
    model = rh.Collection.select_model()
    print('\nmodel={}\n'.format(repr(model)))
    print('import redis_helper as rh\nimport input_helper as ih\n\n')
    embed()


if __name__ == '__main__':
    main()
