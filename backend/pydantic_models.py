from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from fastapi import UploadFile, Query
# Users Model
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    confirmpassword: str = Field(..., min_length=8, max_length=128)

class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)

class UserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    joindate: datetime
    
    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    user_id: int
    username: str
    email: str
    joindate: datetime
    access_token: str
    token_type: str = "bearer"
    profile_picture: str
    description: str

    class Config:
        from_attributes = True

class PreVerifyResponse(BaseModel):
    user_id: int
    email: str
    id: int

    class Config:
        from_attributes = True

class VerifyBase(BaseModel):
    user_id: int
    email: str
    code: int
    id: int

    class Config:
        from_attributes = True
# class OtherUserResponse(BaseModel):
#     user_id: int
#     username: str
#     profile_picture: str
# Movie Model
class MovieBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: str
    movie_length: int
    rating: float = Field(..., ge=0, le=10)
    image_url: Optional[str] = None

class MovieResponse(MovieBase):
    movie_id: int
    release_date: Optional[datetime] = None
    director: str
    genres: list
    actors: list

    class Config:
        from_attributes = True

class AllMoviesInWatchResponse(BaseModel):
    movies: list[MovieResponse]

class SearchParams(BaseModel):
    substring: Optional[str] = None
    release_date: Optional[int] =None
    min_rating: Optional[float] =None
    genres: Optional[List[str]] = None
    sort_by: Optional[str] = None
    page: int

class DirectorToMovieModel(BaseModel):
    movie_id: int
    director_name: str = Field(..., max_length=100)

class ActorToMovieModel(BaseModel):
    movie_id: int
    actor_name: str= Field(..., max_length=100)

class GenresToMovieModel(BaseModel):
    movie_id: int
    genre_name:str = Field(..., max_length=50)

# WatchList Model
class WatchListBase(BaseModel):
    owner: int
    watchlist_title: str = Field(..., max_length=100)

    class Config:
        from_attributes = True

class WatchListCreate(BaseModel):
    owner: int
    watchlist_title: str = Field(..., max_length=100)
    access_token: str

    class Config:
        from_attributes = True

class WatchListResponse(WatchListBase):
    watchlist_id: int
    created_at: datetime
    number_of_movies: int = Field(..., ge=0)
    role: Optional[str] = None
    class Config:
        from_attributes = True

class AllWatchListResponse(BaseModel):
    watchlists: list[WatchListResponse]

    class Config:
        from_attributes = True

class WatchListUpdate(WatchListBase):
    watchlist_id: int
    access_token: str

    class Config:
        from_attributes = True
        
# MoviesInWatchList Model
class MoviesInWatchListBase(BaseModel):
    watchlist_id: int
    movie_id: int
    class Config:
        from_attributes = True
class MoviesInWatchListCreate(BaseModel):
    access_token: str
    watchlist_id: int
    movie_id: int
    user_id: int
    class Config:
        from_attributes = True
class MoviesInWatchListResponse(MoviesInWatchListBase):
    class Config:
        from_attributes = True

# Review Model
# class ReviewBase(BaseModel):
#     user_id: int 
#     movie_id: int
#     rating: float = Field(..., ge=1, le=10)
#     comment: str

# class ReviewCreate(BaseModel):
#     user_id: int 
#     movie_id: int
#     rating: float = Field(..., ge=1, le=10)
#     comment: str
#     access_token: str

# class ReviewResponse(ReviewBase):
#     created_at: datetime
#     username: str
#     class Config:
#         from_attributes = True

# class ReviewsResponse(BaseModel):
#     reviews: list[ReviewResponse]
#     class Config:
#         from_attributes = True

# class ReviewResponseUser(ReviewBase):
#     created_at: datetime
#     class Config:
#         from_attributes = True

# class ReviewsResponseUser(BaseModel):
#     reviews: list[ReviewResponseUser]
#     class Config:
#         from_attributes = True

# Friends Model
class FriendsBase(BaseModel):
    user_one: int
    user_two: int

class FriendRequestCreate(BaseModel):
    user_one: int
    user_two: int
    access_token: str

    
class FriendsResponse(FriendsBase):
    created_at: datetime
    requested_user_accepted: bool
    class Config:
        from_attributes = True

class AllFriendsResponse(BaseModel):
        friends: list[UserResponse]
        class Config:
            from_attributes = True

# Event Model
# class EventBase(BaseModel):
#     event_creator: int
#     event_time: datetime
#     event_name: str = Field(..., max_length=200)
#     event_location: str = Field(..., max_length=200)
#     description: str
#     watchlist_id: Optional[int]
#     is_public: bool
#     class Config:
#         from_attributes = True

# class EventCreate(BaseModel):
#     event_creator: int
#     event_time: datetime
#     event_name: str = Field(..., max_length=200)
#     event_location: str = Field(..., max_length=200)
#     description: str
#     watchlist_id: Optional[int]
#     is_public: bool
#     access_token: str
#     class Config:
#         from_attributes = True

# class EventResponse(EventBase):
#     event_id: int
#     event_creator_name: str
#     class Config:
#         from_attributes = True

# class EventResponseList(BaseModel):
#     events: list[EventResponse]
#     class Config:
#         from_attributes = True

# class EventUpdateResponse(BaseModel):
#     event_id: int
#     event_creator: int
#     event_time: datetime
#     event_name: str = Field(..., max_length=200)
#     event_location: str = Field(..., max_length=200)
#     description: str
#     watchlist_id: Optional[int]
#     is_public: bool
#     access_token: str
# EventInvitees Model
# class EventInviteesBase(BaseModel):
#     event_id: int
#     invitee: int

# class EventInviteesCreate(BaseModel):
#     event_id: int
#     invitee: int
#     access_token: str

# class EventInviteesResponse(EventInviteesBase):
#     class Config:
#         from_attributes = True

# class EventInviteesResponseList(BaseModel):
#     invitees = list

class RecommendationCreate(BaseModel):
    recommender: int
    recommended: int
    movie_id: int
    access_token: str

class RecommendationResponse(BaseModel):
    recommender: int
    recommended: int
    movie_id: int

class RecommendationDelete(BaseModel):
    requesting_user_id: int
    other_user_id: int
    movie_id: int
    is_recommender: bool
    access_token: str


class GuestToWatchlistsCreate(BaseModel):
    watchlist_id: int
    user_id: int
    access_token: str
    role: str

class GuestToWatchlistsResponse(BaseModel):
    watchlist_id: int
    user_id: int
    role: str
    invited_at: datetime
    username: str


    class Config:
        from_attributes = True

class GuestToWatchlistsResponseList(BaseModel):
    guests: list[GuestToWatchlistsResponse]
    class Config:
        from_attributes = True

class MovieRecommendBase(BaseModel):
    title: str = Field(..., max_length=200)
    image_url: Optional[str] = None
    movie_id: int

class GroupedRecommendationResponse(BaseModel):
    recommender: int
    movies: list[MovieRecommendBase]

    class Config:
        from_attributes = True

class UserToMovieModel(BaseModel):
    user_id: int
    movie_id: int
    access_token: str
    times_watched: Optional[int]
    has_watched:Optional[bool]
    is_favorite: Optional[bool]
    watching_now:Optional[bool]
    rating: Optional[float]
    class Config:
        from_attributes = True

class UserMovieInteraction(BaseModel):
    favorite_movies : list
    movie_history : list
    most_watched : list
    watching_now : list

class UserUpdate(BaseModel):
    user_id: int
    username: Optional[str]
    access_key: str
    description: Optional[str]
    isfile: bool