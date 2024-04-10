import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Picture(SqlAlchemyBase):
    __tablename__ = 'picture'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    key = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    long = sqlalchemy.Column(sqlalchemy.Float, nullable=True)
    lat = sqlalchemy.Column(sqlalchemy.Float, nullable=True)
    picture = orm.relationship('Picture')
