import click


@click.command()
def main():
    """Interactively select a Collection model and start ipython shell"""
    from IPython import embed
    import redis_helper as rh
    import input_helper as ih
    from input_helper import matcher
    model = rh.Collection.select_model()
    print(
        '\nimport redis_helper as rh\nimport input_helper as ih\n'
        'from input_helper import matcher\n'
    )
    print('model=rh.{}\n\n'.format(repr(model)))
    embed()


if __name__ == '__main__':
    main()
