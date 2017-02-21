import click
import input_helper as ih
import redis_helper as rh
from input_helper import matcher


class Notes(rh.Collection):
    json_field_list = [
        'allcaps_phrase_list',
        'backtick_list',
        'capitalized_phrase_list',
        'doublequoted_list',
        'line_comment',
        'mention_list',
        'non_comment',
        'paren_group_list',
        'singlequoted_list',
        'tag_list'
    ]
    m = matcher.SpecialTextMultiMatcher()

    def __init__(self, *args, **kwargs):
        kwargs['json_fields'] = ','.join(self.json_field_list)
        super().__init__(*args, **kwargs)

    def parse_and_add(self, text, topic):
        """Parse text using 'self.m' and add using 'self.add'

        For now, the first #tag and @mention will also be separate attributes
        """
        special_text = self.m(text)
        if 'tag_list' in special_text:
            special_text['tag'] = special_text['tag_list'][0]
        if 'mention_list' in special_text:
            special_text['mention'] = special_text['mention_list'][0]
        self.add(text=text, topic=topic, **special_text)


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
        text = ih.user_input(topic, ch)
        if text:
            notes.parse_and_add(text, topic)
        else:
            break


if __name__ == '__main__':
    main()
