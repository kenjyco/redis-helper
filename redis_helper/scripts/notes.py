import click
import input_helper as ih
import redis_helper as rh


notes = rh.Collection(
    'input',
    'note',
    index_fields='topic,tag',
    insert_ts=True
)


@click.command()
@click.option(
    '--ch', '-c', 'ch', default='> ', type=str,
    help='string appended to the topic (default "> ")'
)
@click.argument('topic', nargs=1, default='')
def main(ch, topic):
    print('\nPress <Enter> twice to stop prompting.\n')
    while True:
        text = ih.user_input(topic, ch)
        if text:
            notes.add(topic=topic, text=text)
        else:
            break


if __name__ == '__main__':
    main()
