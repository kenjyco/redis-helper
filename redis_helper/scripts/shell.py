import click
from pprint import pprint


@click.command()
def main():
    """Interactively select a Collection model and start ipython shell"""
    from IPython import embed
    import redis_helper as rh
    import input_helper as ih
    model, *other_models = rh.Collection.select_models()
    print('\nimport redis_helper as rh\nimport input_helper as ih\n')
    print('model=rh.{}\n'.format(repr(model)))
    if other_models:
        print('# Check "other_models" for the {} other model(s) you selected\n\n'.format(
            len(other_models)
        ))
    else:
        print()
    embed()


if __name__ == '__main__':
    main()
