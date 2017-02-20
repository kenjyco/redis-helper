import click
import input_helper as ih
import redis_helper as rh
from input_helper import matcher


json_fields = [
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

notes = rh.Collection(
    'input',
    'note',
    index_fields='topic,tag',
    json_fields=','.join(json_fields),
    insert_ts=True
)

m = matcher.SpecialTextMultiMatcher()


@click.command()
@click.option(
    '--ch', '-c', 'ch', default='> ', type=str,
    help='string appended to the topic (default "> ")'
)
@click.argument('topic', nargs=1, default='')
def main(ch, topic):
    """Prompt user to enter notes (about a topic) until finished"""
    print('\nPress <Enter> twice to stop prompting.\n')
    while True:
        text = ih.user_input(topic, ch)
        if text:
            special_text = m(text)
            if 'tag_list' in special_text:
                special_text['tag'] = special_text['tag_list'][0]
            notes.add(topic=topic, text=text, **special_text)
        else:
            break


if __name__ == '__main__':
    main()
