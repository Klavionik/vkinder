"""
VKinder: a coursework for Netology Python course by Roman Vlasenko

GOAL: implement a Tinder-like app which, given a VK user id
or a screenname, finds the most compatible pairs for the user
amongst the other VK users.

The application collects all the information it needs
through the VK API and user input, finds the matches,
assigns each match a score based on the likeness of
user's and match's profile, saves matches to the database
and prints out matches from the database in descending score order.
"""
import sys

from vkinder import R, G, Y, V, END, B


def run(app):
    """
    Options:

        u (user) - set current app user
        f (find) - find/refresh matches for the current user
        d (delete) - delete user and all their matches
        n (next) - show next best matches for a user
        l (list) - list saved users
        q (quit) - quit app
    """

    print(f'{B}{__doc__}{END}')

    while True:
        print(f'{B}{run.__doc__}{END}')
        print(f"{B}Current user: "
              f"{app.current_user.full_name if app.current_user else 'Not set'}\n")
        option = input().rstrip().lower()

        if option == 'u':
            set_user(app)
        elif option == 'f':
            find_matches(app)
        elif option == 'd':
            delete_user(app)
        elif option == 'n':
            next_matches(app)
        elif option == 'l':
            list_users(app)
        elif option == 'q':
            sys.exit()


def set_user(app):
    target = input(f"{Y}Let's find somebody's fortune! "
                   "Enter their ID or screenname below.\n"
                   f"We'll need to acquire some information.{END}\n")
    if not target:
        return
    new_user = app.set_user(target)
    if new_user is False:
        print(f"{Y}This profile is private, deleted or banned.{END}")
    elif new_user is None:
        print(f"{Y}Can't find user with this name.{END}")
    else:
        print(f'{G}{new_user} set as the current user.{END}')


def delete_user(app):
    target = input(f"{Y}Enter user id to delete their profile from the database.{END}\n")
    if not target or not isinstance(target, int):
        return
    deleted = app.delete_user(target)
    if not deleted:
        print(f"{Y}Can't find user with ID {target}. Maybe you've made a typo.{END}")
    else:
        print(f'{G}User with ID {target} and all the corresponding matches '
              f'have been deleted.{END}')


def find_matches(app):
    if app.current_user:
        print(f"\n{G}Please, wait a minute while we're collecting data...{END}\n")
        found = app.spawn_matches()
        print(f'\n{G}{found} matches found and saved.{END}')
    else:
        print(f'{R}No current user set.{END}')


def next_matches(app):
    if not app.current_user:
        target = input(f'{Y}No current user set.\n'
                       f'Enter user id to get next {app.output_amount} matches.{END}\n')
    else:
        target = app.current_user.uid

    matches = app.next_matches(target)
    if matches is not False and isinstance(matches, int):
        print(f'{G}{matches} records exported to the data folder.{END}')
    elif matches is not False and isinstance(matches, dict):
        for match in matches.values():
            print(f'{V}{match["name"]} '
                  f'{match["surname"]} '
                  f'{match["profile"]} '
                  f'Total score: {match["total_score"]}{END}')
            print("Best photos:")
            for photo in match['photos']:
                print(photo)
            print()
    else:
        print(f'{R}User not found.{END}')


def list_users(app):
    users_list = app.list_users()
    if users_list is not False:
        for user in users_list:
            print(f'{G}{user["name"]} {user["surname"]} '
                  f'Age {user["age"]} ID {user["uid"]}{END}')
    else:
        print(f'{R}No saved users.{END}')
