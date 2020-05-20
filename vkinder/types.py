import os
import pickle
from datetime import datetime

import vkinder.utils as utils
from . import config, Y, END, resources

# VK user object item fields -> :class:`User` attributes mapping
user_map = {'general': config['General User'],
            'interests': config['Interests'],
            'personal': config['Personal']}

# VK user object item fields -> :class:`Match` attributes mapping
match_map = {'general': config['General Match'],
             'interests': config['Interests'],
             'personal': config['Personal']}

# Match settings: score weight
PERSONAL_FACTOR = config.getint('Match Settings', 'PersonalFactor')
INTERESTS_FACTOR = config.getint('Match Settings', 'InterestsFactor')
FRIENDS_FACTOR = config.getint('Match Settings', 'FriendsFactor')
GROUPS_FACTOR = config.getint('Match Settings', 'GroupsFactor')
AGE_BOUND = config.getint('Match Settings', 'AgeBound')


class User:

    def __init__(self, uid,
                 name,
                 surname,
                 sex,
                 age,
                 city,
                 personal,
                 interests,
                 groups):

        self.uid = uid
        self.name = name
        self.surname = surname
        self.sex = sex
        self.age = age
        self.city = city
        self.interests = interests
        self.personal = personal
        self.groups = groups

    def __repr__(self):
        return f'User {self.name} {self.surname}'

    @classmethod
    def from_api(cls, profile, groups):
        general, personal, interests = cls.parse(profile)
        return cls(general['uid'],
                   general['name'],
                   general['surname'],
                   general['sex'],
                   general['age'],
                   general['city'], personal, interests, groups)

    @classmethod
    def from_database(cls, db_user):

        interests = pickle.loads(db_user.interests)
        personal = pickle.loads(db_user.personal)
        groups = pickle.loads(db_user.groups)

        return cls(db_user.uid,
                   db_user.name,
                   db_user.surname,
                   db_user.sex,
                   db_user.age,
                   db_user.city, personal, interests, groups)

    @classmethod
    def parse(cls, profile):
        """
        Takes a VK API `User` object in the form of a dictionary and prepares its contents
        in order to create a :class:`User` object.

        :param profile: Dictionary describing a VK API `User` object
        :return: Parsed user profile info
        """
        flat_profile = utils.flatten(profile)
        bad_value = ''

        general = {}
        personal = {}
        interests = {}

        for category, mapping in user_map.items():
            for vk_field, cls_attr in mapping.items():
                value = flat_profile.get(vk_field, '')
                if vk_field == 'bdate':
                    value = cls.find_age(value)
                elif not value or value == bad_value:
                    value = cls.ask_user(cls_attr)

                if category == 'personal':
                    personal[cls_attr] = value
                elif category == 'interests':
                    clean_attr = utils.cleanup(value)
                    interests[cls_attr] = clean_attr
                else:
                    general[cls_attr] = value

        return general, personal, interests

    @classmethod
    def ask_user(cls, attribute):
        """
        Handles the case, when user information is incomplete and requires clarification.

        :param attribute: Attribute of :class:`User`
        :return: Attribute's value
        """
        path = os.path.join(resources, 'output', attribute)

        with open(f'{path}.txt', encoding='utf8') as f:
            question = f.read().strip()
        answer = input(f'\n{question}\n\n')

        if answer.isdigit():
            answer = int(answer)

        return answer

    @classmethod
    def find_age(cls, bday):
        """
        Takes the current user's birth date and returns their age.

        :param bday: Birth date
        :return: Exact user age
        """
        if not utils.verify_bday(bday):
            bday = input('\nBirth date is incomplete or incorrect.\n'
                         'Please, enter your birth date as dd.mm.yyyy.\n\n')

        try:
            bday = datetime.strptime(bday, '%d.%m.%Y')
        except ValueError:
            print(f"{Y}Invalid data format. Age set to 18.{END}")
            return 18

        today = datetime.today()
        return today.year - bday.year - ((today.month, today.day) < (bday.month, bday.day))

    def search_criteria(self, ignore_city, ignore_age, same_sex):
        age_bound = AGE_BOUND if not ignore_age else 100
        criteria = {'city': 0 if ignore_city else self.city,
                    'sex': utils.target_sex(self.sex, same_sex),
                    'age_from': self.age - age_bound if (self.age - age_bound) >= 18 else 18,
                    'age_to': self.age + age_bound,
                    'has_photo': 1,
                    'count': 1000,
                    'fields': 'blacklisted,'
                              'blacklisted_by_me,'
                              'relation'}
        return criteria

    @property
    def full_name(self):
        return f'{self.name} {self.surname}'


class Match:

    def __init__(self, uid,
                 name,
                 surname,
                 common_friends,
                 interests,
                 personal,
                 groups,
                 photos):

        self.uid = uid
        self.name = name
        self.surname = surname
        self.common_friends = common_friends
        self.interests = interests
        self.personal = personal
        self.groups = groups
        self.photos = photos

        self.score = 0
        self.interests_score = 0
        self.personal_score = 0
        self.friends_score = 0
        self.groups_score = 0

    def __repr__(self):
        return f'Match {self.name} {self.surname}'

    @classmethod
    def from_api(cls, profile, groups, photos):
        general, personal, interests = cls.parse(profile)
        return cls(general['uid'],
                   general['name'],
                   general['surname'],
                   general['common_friends'],
                   personal, interests, groups, photos)

    @classmethod
    def parse(cls, info):
        """
        Takes a VK API `User` object in the form of a dictionary and prepares its contents
        in order to create a :class:`Match` object.

        :param info: Dictionary describing a VK API `User` object
        :return: Parsed user profile info
        """
        flat_response = utils.flatten(info)

        general = {}
        personal = {}
        interests = {}

        for category, mapping in match_map.items():
            for vk_field, cls_attr in mapping.items():
                value = flat_response.get(vk_field, '')
                if vk_field == 'common_friends' and not value:
                    value = 0

                if category == 'personal':
                    personal[cls_attr] = value
                elif category == 'interests':
                    clean_value = utils.cleanup(value)
                    interests[cls_attr] = clean_value
                else:
                    general[cls_attr] = value

        return general, personal, interests

    @property
    def total_score(self):
        return self.score + self.interests_score + \
               self.personal_score + self.friends_score + \
               self.groups_score

    @property
    def profile(self):
        return f"https://vk.com/id{self.uid}"

    def scoring(self, model):
        self.interests_score = self._score_interests(model)
        self.personal_score = self._score_personal(model)
        self.friends_score = self._score_friends()
        self.groups_score = self._score_groups(model)

    def _score_interests(self, model):
        interests_score = 0

        for field in model.interests:
            user_value = model.interests[field]
            match_value = self.interests.get(field, None)
            if match_value:
                field_score = INTERESTS_FACTOR * utils.common(match_value, user_value)
                interests_score += field_score
        return interests_score

    def _score_personal(self, model):
        personal_score = 0

        for field in model.personal:
            user_value = model.personal[field]
            match_value = self.personal.get(field, None)
            if match_value == user_value:
                personal_score += PERSONAL_FACTOR * 1
        return personal_score

    def _score_friends(self):
        friends_score = 0

        friends_score += FRIENDS_FACTOR * self.common_friends

        return friends_score

    def _score_groups(self, model):
        groups_score = 0

        groups_score += GROUPS_FACTOR * utils.common(self.groups, model.groups)

        return groups_score
