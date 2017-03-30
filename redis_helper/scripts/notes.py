import click
import input_helper as ih
import redis_helper as rh


class Notes(rh.Collection):
    def __init__(self, *args, **kwargs):
        kwargs['json_fields'] = ','.join(ih.SPECIAL_TEXT_RETURN_FIELDS)
        super().__init__(*args, **kwargs)

    def add_parsed(self, parsed_text, topic):
        """Modify parsed_text and add using 'self.add'

        For now, the first #tag and @mention will also be separate attributes
        """
        if 'tag_list' in parsed_text:
            parsed_text['tag'] = parsed_text['tag_list'][0]
        if 'mention_list' in parsed_text:
            parsed_text['mention'] = parsed_text['mention_list'][0]
        self.add(topic=topic, **parsed_text)


notes = Notes(
    'input',
    'note',
    index_fields='topic,tag,mention',
    insert_ts=True
)


@click.command()
@click.option(
    '--ch', '-c', 'ch', default='> ', type=str,
    help='string appended to the topic (default "> ")'
)
@click.option(
    '--shell', '-s', 'shell', is_flag=True, default=False,
    help='Start an ipython shell to inspect the notes collection'
)
@click.argument('topic', nargs=1, default='')
def main(ch, shell, topic):
    """Prompt user to enter notes (about a topic) until finished; or review notes"""
    if shell:
        from IPython import embed
        print('\nInspect the "notes" object...\n')
        embed()
        return

    print('\nPress <Enter> twice to stop prompting.\n')
    while True:
        parsed_text = ih.user_input_fancy(topic, ch)
        if parsed_text['text']:
            notes.add_parsed(parsed_text, topic)
        else:
            break


if __name__ == '__main__':
    main()
