from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Float, Text, PrimaryKeyConstraint, Index, CheckConstraint, Enum
from sqlalchemy.orm import relationship
#from backend.main import Base
from database import Base
from datetime import datetime
import enum
from datetime import datetime, timedelta

class Users(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    joindate = Column(DateTime, nullable=False, default=datetime.now)
    password = Column(String(128), nullable=False)
    session_at =  Column(DateTime, nullable=True)
    access_key = Column(String(400), nullable = True)
    profile_picture = Column(String(400), nullable = False, default= "")
    description = Column(String(800), nullable = False, default= "")
    is_verified = Column(Boolean, nullable = False, default = False)


class Verification(Base):
    __tablename__ = "verification"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = Column(Integer,  ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    email = Column(String(100), nullable=False)    
    code = Column(String(6), nullable=False)      
    type = Column(String(20), nullable=False)     
    created_at = Column(DateTime, nullable=False, default=datetime.now())
    expires_at = Column(DateTime, nullable=False, default=lambda: datetime.now() + timedelta(minutes=10))
    is_used = Column(Boolean, nullable=False, default=False)
    ForeignKey("users.user_id", ondelete="CASCADE")


class Movie(Base):
    __tablename__ = "movie"
    movie_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    movie_length = Column(Integer, nullable=False)
    rating = Column(Float, nullable=False)
    image_url =Column(Text)
    release_date = Column(DateTime, default=datetime.now)

    __table_args__ = (
        CheckConstraint('movie_length > 0', name='check_movie_length'),
        CheckConstraint('rating BETWEEN 0 AND 10', name='check_rating_range'),
        Index('idx_movie_rating', 'rating'),
    )
    directors = relationship("DirectorToMovie", back_populates="movie", cascade="all, delete-orphan")
    actors = relationship("ActorToMovie", back_populates="movie", cascade="all, delete-orphan")
    genres = relationship("GenresToMovie", back_populates="movie", cascade="all, delete-orphan")


class DirectorToMovie(Base):
    __tablename__ = "directortomovie"
    movie_id = Column(Integer, ForeignKey("movie.movie_id", ondelete="CASCADE"), primary_key=True, nullable=False)
    director_name = Column(String, primary_key=True, nullable=False)

    __table_args__ = (Index('ix_director_movie', 'movie_id', 'director_name'),)
    movie = relationship("Movie", back_populates="directors")


class ActorToMovie(Base):
    __tablename__ = "actortomovie"
    movie_id = Column(Integer, ForeignKey("movie.movie_id", ondelete="CASCADE"), primary_key=True, nullable=False)
    actor_name = Column(String, primary_key=True, nullable=False)

    __table_args__ = (Index('ix_actor_movie', 'movie_id', 'actor_name'),)
    movie = relationship("Movie", back_populates="actors")

class GenresToMovie(Base):
    __tablename__ = "genrestomovie"
    movie_id = Column(Integer, ForeignKey("movie.movie_id", ondelete="CASCADE"), primary_key=True, nullable=False)
    genre_name = Column(String(50), primary_key=True, nullable=False)

    __table_args__ = (
        Index('ix_genre_movie', 'movie_id', 'genre_name'),
        PrimaryKeyConstraint('movie_id', 'genre_name', name='unique_movie_genre')
    )
    movie = relationship("Movie", back_populates="genres")

class WatchList(Base):
    __tablename__ = "watchlist"
    watchlist_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    owner = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    number_of_movies = Column(Integer, nullable=False)
    watchlist_title = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    movies = relationship("MoviesInWatchList", back_populates="watchlist", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint('number_of_movies >= 0', name='check_positive_movie_count'),
        Index('idx_watchlist_owner', 'owner')
    )

class MoviesInWatchList(Base):
    __tablename__ = "moviesinwatchlist"
    watchlist_id = Column(Integer, ForeignKey("watchlist.watchlist_id", ondelete="CASCADE"), primary_key=True, nullable=False)
    movie_id = Column(Integer, ForeignKey("movie.movie_id", ondelete="CASCADE"), primary_key=True, nullable=False)
    watchlist = relationship("WatchList", back_populates="movies")

    __table_args__ = (Index('ix_watchlist_movie', 'watchlist_id', 'movie_id'),)

# class Review(Base):
#     __tablename__ = "review"
#     user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True, nullable=False)
#     movie_id = Column(Integer, ForeignKey("movie.movie_id", ondelete="CASCADE"), primary_key=True, nullable=False)
#     created_at = Column(DateTime, nullable=False, default=datetime.now)
#     rating = Column(Float, nullable=False)
#     comment = Column(Text, nullable=False)

class Friends(Base):
    __tablename__ = "friends"
    user_one = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True, nullable=False)
    user_two = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    requested_user_accepted = Column(Boolean, nullable=False, default=False)
    __table_args__ = (
        Index('ix_user_friends', 'user_one', 'user_two'),
        PrimaryKeyConstraint('user_one', 'user_two', name='unique_friends_pair')
    )

class Event(Base):
    __tablename__ = "event"
    event_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    event_creator = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    event_time = Column(DateTime, nullable=False, default=datetime.now)
    event_name = Column(String(200), nullable=False)
    event_location = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    watchlist_id = Column(Integer, ForeignKey("watchlist.watchlist_id"),nullable=True)
    is_public = Column(Boolean, nullable=False, default=False )

class EventInvitees(Base):
    __tablename__ = "eventinvitees"
    event_id = Column(Integer, ForeignKey("event.event_id", ondelete="CASCADE"), primary_key=True, nullable=False)
    invitee = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True, nullable=False)

    __table_args__ = (Index('ix_event_invitee', 'event_id', 'invitee'),)

class WatchlistRole(enum.Enum):
    VIEWER = "VIEWER"
    EDITOR = "EDITOR"

class GuestToWatchlists(Base):
    __tablename__ = "gueststowatchlists"
    watchlist_id = Column(Integer, ForeignKey("watchlist.watchlist_id"), primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True, nullable=False)
    invited_at = Column(DateTime, nullable=False, default=datetime.now)
    role = Column(Enum(WatchlistRole), nullable=False, default=WatchlistRole.VIEWER) 
    
class Recommendation(Base):
    __tablename__ = "recommendation"

    recommender = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    recommended = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movie.movie_id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("recommender", "recommended", "movie_id"),
    )

class UserToMovie(Base):
    __tablename__ = "usertomovie"

    user_id =  Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False,primary_key=True)
    movie_id = Column(Integer, ForeignKey("movie.movie_id", ondelete="CASCADE"), primary_key=True, nullable=False)
    times_watched = Column(Integer, nullable=False, default=0)
    has_watched = Column(Boolean, default=False,nullable=False)
    is_favorite = Column(Boolean, default=False,nullable=False)
    watching_now = Column(Boolean, default=False,nullable=False)
    rating = Column(Float, nullable=False, default=0)
    __table_args__ = (
        CheckConstraint('times_watched >= 0', name='check_positive_movie_count'),
        CheckConstraint('rating BETWEEN 0 AND 10', name='check_rating_range'),
    )
