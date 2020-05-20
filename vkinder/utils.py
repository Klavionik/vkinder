import os
import re
import sys

import progressbar

from . import config, END, V, B

# VK photo sizes map (from biggest to smallest)
photo_sizes = {k: int(v) for k, v in config['Photo Sizes'].items()}


def cleanup(text):
    """
    Takes a given text and processes it to prepare for match scoring.

    1) Removes meaningless characters from the text
    2) Replaces all occurences of a newline with a comma
    3) Splits the text using comma as a delimiter
    4) Converts every string of the splitted text for lowercase
    and removes whitespace characters on both ends of a string

    :param text: Text string
    :return: List of strings
    """
    special_characters = re.compile(r'[\"^;!/|()«»]', re.IGNORECASE)
    newline = re.compile(r'\n')
    no_spec_char = special_characters.sub('', text)
    no_newlines = newline.sub(',', no_spec_char)
    final = [key.lower().strip() for key in no_newlines.split(',')]

    return final


def common(iterable1, iterable2):
    return len(set(iterable1) & set(iterable2))


def find_largest_photo(links):
    """
    Given the 'sizes' array of a VK API `Photo` object, returns a
    link to the largest photo in the array.

    :param links: `Sizes` array
    :return: Largest photo url
    """

    def size_type_to_int(size):
        return photo_sizes[size]

    return sorted(links, key=lambda x: size_type_to_int(x['type']), reverse=True)[0]['url']


def flatten(d):
    """
    Flattens a dictionary containing other dictionaries.

    :param d: Dictionary of dictionaries
    :return: Flat dictionary
    """
    flat = {}
    for key, value in d.items():
        if isinstance(value, dict):
            for subkey, subvalue in d[key].items():
                flat[key + '.' + subkey] = subvalue
        else:
            flat[key] = value

    return flat


def next_ids(ids, amount=12):
    """
    Splits a list of matches ids in chunks.

    :param ids: List of matches ids
    :param amount: Amount of ids yielded per iteration
    """
    for index in range(0, len(ids), amount):
        yield ids[index:index + amount]


def verify_bday(value):
    """
    Validates if a given string conforms to the format used for find_age function.
    """
    pattern = re.compile(r'^\d?\d\.\d?\d\.\d{4}$')

    try:
        verification = re.match(pattern, value)
    except TypeError:
        return None
    else:
        return True if verification else False


def progress_bar(text):
    bar = \
        progressbar.ProgressBar(widgets=[f'{B}{text}{END}',
                                         progressbar.Percentage(),
                                         progressbar.Bar(
                                             marker=progressbar.AnimatedMarker(
                                                 fill='#', fill_wrap=(f'{V}', f'{END}'),
                                                 marker_wrap=(f'{V}', f'{END}'))
                                         )
                                         ],
                                redirect_stdout=True)
    return bar


def target_sex(user_sex, same_sex):
    if not same_sex:
        if user_sex == 2:
            return 1
        else:
            return 2
    else:
        if user_sex == 2:
            return 2
        else:
            return 1


def clean_screen():
    if sys.platform == "win32":
        os.system("cls")
    elif sys.platform == "linux":
        os.system("printf '\033c'")
