import json
import os
import sys
from time import sleep

import vkinder.utils as utils
from . import config
from . import resources, data, G, END, dbpath
from .api import VKApi, check_profile
from .db import AppDB, db_session
from .exceptions import UserUnavailable, InvalidUserID
from .types import User, Match

API_URL = config.get('VK API', 'APIUrl')
VERSION = config.get('VK API', 'Version')


class App:

    def __init__(self, api, export, output_amount, ignore_city, ignore_age, same_sex, db):
        self.api = api
        self.db = AppDB(db)
        self.export = export
        self.output_amount = output_amount
        self.ignore_city = ignore_city
        self.ignore_age = ignore_age
        self.same_sex = same_sex

        self.current_user = None

    def set_user(self, id_or_screenname):
        try:
            user_response = self._fetch_user(id_or_screenname)
        except UserUnavailable:
            return False
        except InvalidUserID:
            return None

        user_id = user_response[0]['id']
        user_profile = user_response[0]

        with db_session(self.db.factory) as session:
            user_in_db = self.db.get_user(user_id, session)

            if user_in_db:
                user = User.from_database(user_in_db)
                self.current_user = user
                print(f'\n{G}{user} loaded from the database.{END}')
            else:
                user = self.new_user(user_id, user_profile, session)
                self.current_user = user
                print(f'\n{G}{user} loaded from the API{END}')

        return str(self.current_user)

    def new_user(self, user_uid, user_profile, session):
        if not user_profile.get('city', None):
            city = input("\nLooks like we don't know, where you live.\n"
                         "What's your city of residence?\n\n")
            city_id = self.api.other.getcities(country_id=1,
                                               city=city,
                                               count=1)['items'][0]['id']
            user_profile['city.id'] = city_id

        user_groups = self._fetch_user_groups(user_uid)
        user = User.from_api(user_profile, user_groups)
        self.db.add_user(user, session)

        return user

    def delete_user(self, user_uid):
        if self.current_user and (self.current_user.uid == int(user_uid)):
            self.current_user = None

        with db_session(self.db.factory) as session:
            if user := self.db.get_user(user_uid, session):
                self.db.delete_user(user, session)
                return True
            return False

    def spawn_matches(self):
        if not self.current_user:
            return False

        profiles, groups, photos = self._prepare_matches()

        bar = utils.progress_bar("Building matches: ")

        for match_info, match_groups, match_photos in \
                bar(zip(profiles, groups, photos),
                    max_value=len(profiles)):
            top3_photos = self._get_top3_photos(match_photos)
            match_object = Match.from_api(match_info, match_groups, top3_photos)
            match_object.scoring(self.current_user)

            with db_session(self.db.factory) as session:
                if match_in_db := self.db.get_match(match_object.uid,
                                                    self.current_user.uid,
                                                    session):
                    self.db.update_match(match_in_db, match_object, session)
                else:
                    self.db.add_match(match_object, self.current_user.uid, session)

        return len(profiles)

    def list_users(self):
        with db_session(self.db.factory) as session:
            all_users = self.db.get_all_users(session)
            if all_users:
                return self._make_list(all_users)
            else:
                return False

    def next_matches(self, user_id):
        with db_session(self.db.factory) as session:
            user = self.db.get_user(user_id, session)

            if user:
                next_matches = self.db.pop_match(user_id, self.output_amount, session)
            else:
                return False

        if self.export:
            path = os.path.join(data, f'{user_id}_matches.json')
            with open(path, 'w', encoding='utf8') as f:
                json.dump(next_matches, f, indent=2, ensure_ascii=False)
                return len(next_matches)
        else:
            return next_matches

    @check_profile
    def _fetch_user(self, identificator):
        fields = ','.join(['bdate', 'city', 'sex',
                           'games', 'music', 'movies', 'interests',
                           'tv', 'books', 'personal'])
        api_response = self.api.users.get(user_ids=identificator,
                                          fields=fields)

        return api_response

    def _fetch_user_groups(self, user_id):

        user_groups = self.api.groups.get(user_id=user_id)
        return user_groups['items']

    def _prepare_matches(self):
        search_criteria = self.current_user.search_criteria(self.ignore_city,
                                                            self.ignore_age,
                                                            self.same_sex)
        profiles, groups, photos = self._find_matches(search_criteria)

        return profiles, groups, photos

    def _find_matches(self, search_criteria):
        rough_matches = self.api.users.search(**search_criteria)['items']
        fine_matches = self._sifter(rough_matches)

        fields = ','.join([
            'bdate', 'city', 'sex', 'common_count'
                                    'games', 'music', 'movies', 'interests',
            'tv', 'books', 'personal'
        ])

        profiles = self.api.users.get(
            user_ids=','.join(fine_matches),
            fields=fields)
        groups, photos = self._get_groups_photos(fine_matches)

        return profiles, groups, photos

    @staticmethod
    def _sifter(rough_matches):
        """
        Loops through the list of possible matches and filters out unneeded ones.

        For every match, checks
        1) that the match doesn't have the current user blacklisted
        2) that the match is not in the blacklist of a current user
        3) that the match don't any personal relations
        4) that the match's VK profile is not private

        If all these conditions are met, then the function adds a match id to
        to the final list of matches.

        :param rough_matches: List of VK `User` objects.
        :return: List of matches ids.
        """
        bar = utils.progress_bar('Sorting out data: ')

        sifted = []

        for match in bar(rough_matches, max_value=len(rough_matches)):
            if (not match['blacklisted']) and \
                    (not match['blacklisted_by_me']) and \
                    (match.get('relation', 0) not in (2, 3, 4, 7, 8)) and \
                    not match['is_closed']:
                sifted.append(str(match['id']))
                sleep(0.010)

        return sifted

    @staticmethod
    def _prepare_code(ids):
        path = os.path.join(resources, 'vkscript.txt')

        with open(path, encoding='utf8') as f:
            code = f.read()

        return code % (ids, len(ids))

    def _get_groups_photos(self, matches_ids):
        """
        Loops through the list of matches ids and gets groups
        and photos info for every id.

        Due to a limitation set by the VK API you can't make more than
        3 API requests per second. To circumvent this limitation
        the `execute` method of the API is used.

        `Execute` method accepts code written in VKScript format
        and allows that code to make up to 25 requests per one
        `execute` method execution.

        :param matches_ids: List of matches ids.
        :return: Tuple of dicts (matches groups, matches photos).
        """
        matches_groups = []
        matches_photos = []

        bar = utils.progress_bar('Fetching profiles: ')

        for ids_chunk in bar(utils.next_ids(matches_ids),
                             max_value=len(matches_ids) / 12):
            code = self._prepare_code(ids_chunk)
            result = self.api.other.execute(code=code)
            groups, photos = result[0], result[1]
            matches_groups.extend(groups)
            matches_photos.extend(photos)

        return matches_groups, matches_photos

    @staticmethod
    def _get_top3_photos(profile_photos):
        photos_processed = [{'likes': photo['likes']['count'],
                             'link': utils.find_largest_photo(photo['sizes'])}
                            for photo in profile_photos]

        return sorted(photos_processed,
                      key=lambda photo: photo['likes'],
                      reverse=True)[:3]

    @staticmethod
    def _make_list(db_users_list):
        users_list = [{'name': user.name, 'surname': user.surname,
                       'age': user.age, 'uid': user.uid}
                      for user in db_users_list]

        return users_list


def startup(flags):
    export = flags['export']
    output_amount = flags['output_amount']
    ignore_city = flags.get('ignore_city', False)
    ignore_age = flags.get('ignore_age', False)
    same_sex = flags['same_sex']
    debug = flags['debug']

    try:
        os.mkdir(data)
    except FileExistsError:
        pass

    if sys.platform.startswith('win'):
        os.system('color')

    utils.clean_screen()

    api = VKApi(API_URL, VERSION, debug)

    return App(api, export, output_amount,
               ignore_city, ignore_age, same_sex, dbpath)
