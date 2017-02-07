import click


@click.command()
def main():
    from IPython import embed
    import redis_helper as rh
    model = rh.Collection.select_model()
    print('\nmodel={}\n'.format(repr(model)))
    embed()


if __name__ == '__main__':
    main()
