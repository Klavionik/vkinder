import pickle
from contextlib import contextmanager

from sqlalchemy import Column, Integer, String, BLOB, Boolean, ForeignKey
from sqlalchemy import create_engine, desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from . import R, END

Base = declarative_base()


@contextmanager
def db_session(factory):
    """
    Provides a session scope for database operations.
    :param factory: SQLAlchemy session constructor object
    """
    session = factory()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        print(f'{R}Database Error:{END}', e.args[0])
        session.rollback()
    finally:
        session.close()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    uid = Column(Integer, unique=True)
    name = Column(String)
    surname = Column(String)
    sex = Column(Integer)
    age = Column(Integer)
    city = Column(Integer)
    interests = Column(BLOB)
    personal = Column(BLOB)
    groups = Column(BLOB)
    matches = relationship('Match', cascade='save-update, merge, delete')

    def __repr__(self):
        return f'User ID{self.uid} Name: {self.name} Surname: {self.surname}'


class Match(Base):
    __tablename__ = 'matches'

    id = Column(Integer, primary_key=True)
    uid = Column(Integer)
    user_uid = Column(Integer, ForeignKey('users.uid'))
    name = Column(String)
    surname = Column(String)
    profile = Column(String(32))
    total_score = Column(Integer)
    seen = Column(Boolean, default=False)
    photos = relationship('Photo', cascade='save-update, merge, delete')

    def __repr__(self):
        return f'Match ID{self.uid} Name: {self.name} Surname: {self.surname}'


class Photo(Base):
    __tablename__ = 'photos'

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey('matches.id'))
    link = Column(String)


class AppDB:

    def __init__(self, db_url):
        """
        Initializes a database connection, creates tables if they don't exist,
        creates a session factory.

        :param db_url: Path to the database file
        """
        self.db = create_engine(f'sqlite:///{db_url}')
        Base.metadata.create_all(self.db)
        self.factory = sessionmaker(bind=self.db)

    @staticmethod
    def add_user(user_object, session):
        new_user = User(uid=user_object.uid,
                        name=user_object.name,
                        surname=user_object.surname,
                        sex=user_object.sex,
                        age=user_object.age,
                        city=user_object.city,
                        interests=pickle.dumps(user_object.interests),
                        personal=pickle.dumps(user_object.personal),
                        groups=pickle.dumps(user_object.groups))

        session.add(new_user)

    @staticmethod
    def add_match(match_object, user_uid, session):
        new_match = Match(uid=match_object.uid,
                          user_uid=user_uid,
                          name=match_object.name,
                          surname=match_object.surname,
                          profile=match_object.profile,
                          total_score=match_object.total_score)

        session.add(new_match)
        session.flush()

        photos = [Photo(match_id=new_match.id,
                        link=photo['link'])
                  for photo in match_object.photos]

        session.add_all(photos)

    @staticmethod
    def update_match(match_record, match_object, session):

        match_record.profile = match_object.profile
        match_record.total_score = match_object.total_score

        photos = session.query(Photo).filter(Photo.match_id == match_record.id).all()
        for index, photo in enumerate(photos):
            photo.link = match_object.photos[index]['link']

    @staticmethod
    def delete_user(user_record, session):
        session.delete(user_record)
        return True

    @staticmethod
    def delete_photos(photos_records, session):
        for record in photos_records:
            session.delete(record)

    @staticmethod
    def get_user(user_uid, session):
        user = session.query(User).filter(User.uid == user_uid).first()

        if user:
            return user

    @staticmethod
    def get_match(match_uid, user_uid, session):
        query = session.query(Match)
        filtered = query.filter(Match.uid == match_uid, Match.user_uid == user_uid)
        match = filtered.first()

        if match:
            return match

    @staticmethod
    def pop_match(user_uid, count, session):
        matches = {}

        match_query = session.query(Match)
        photos_query = session.query(Photo.link)

        for match in match_query. \
                filter(Match.user_uid == user_uid, ~ Match.seen). \
                order_by(desc(Match.total_score)).limit(count):
            matches[match.id] = {'name': match.name,
                                 'surname': match.surname,
                                 'profile': match.profile,
                                 'total_score': match.total_score}

            photos = photos_query.filter(Photo.match_id == match.id).all()
            matches[match.id]['photos'] = [photo[0] for photo in photos]
            match.seen = True

        return matches

    @staticmethod
    def get_all_users(session):
        users = session.query(User).all()

        if users:
            return users
