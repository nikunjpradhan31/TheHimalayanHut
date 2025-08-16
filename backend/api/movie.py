from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
# from backend.models import *
# from backend.pydantic_models import *
# from backend.database import get_db
from models import *
from pydantic_models import *
from database import SyncSessionLocal, get_db
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import func, distinct, extract
from .recommendations import get_recommendation_eng_movies

router = APIRouter(prefix="/movie", tags=["movie"])

def check_valid_request(user_id, access_token, db):
    User = db.query(Users).filter(Users.user_id == user_id).first()
    if User == None  or User.access_key != access_token:
        return False
    return True

@router.get("/get/{movie_id}", response_model=MovieResponse)
def get_movie_details(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(Movie)\
        .options(
            joinedload(Movie.genres),
            joinedload(Movie.actors),
            joinedload(Movie.directors)
        )\
        .filter(Movie.movie_id == movie_id)\
        .first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This movie does not exist"
        )

    genre_names = [genre.genre_name for genre in movie.genres]
    actor_names = [actor.actor_name for actor in movie.actors]
    director_name = movie.directors[0].director_name if movie.directors else None

    return MovieResponse(
        title=movie.title,
        description=movie.description,
        movie_length=movie.movie_length,
        rating=movie.rating,
        image_url=movie.image_url,
        movie_id=movie.movie_id,
        release_date=movie.release_date,
        director=director_name,
        genres=genre_names,
        actors=actor_names
    )

@router.get("/get_genres")
def get_genres(db: Session = Depends(get_db)):
    genres = db.query(GenresToMovie.genre_name).distinct().all()
    genres_list = [genre[0] for genre in genres]
    return genres_list

@router.post("/search", status_code=status.HTTP_200_OK)
def fetch_movies(
    input: SearchParams,
    db: Session = Depends(get_db),
):
    print(input)

    movies_per_page = 16
    offset = (input.page - 1) * movies_per_page

    base_query = db.query(Movie)

    if input.substring:
        base_query = base_query.filter(Movie.title.ilike(f"%{input.substring}%"))
    if input.release_date:
        base_query = base_query.filter(extract('year', Movie.release_date) == input.release_date)

    if input.min_rating:
        base_query = base_query.filter(Movie.rating >= input.min_rating)
    if input.genres:
        genre_count = len(input.genres)

        genre_movie_ids = (
            db.query(GenresToMovie.movie_id)
            .filter(GenresToMovie.genre_name.in_(input.genres))
            .group_by(GenresToMovie.movie_id)
            .having(func.count(distinct(GenresToMovie.genre_name)) == genre_count)
            .subquery()
        )

        base_query = base_query.filter(Movie.movie_id.in_(genre_movie_ids))


    # Get distinct count of movies before applying offset and limit
    total_movies = base_query.distinct(Movie.movie_id).count()
    total_pages = (total_movies + movies_per_page - 1) // movies_per_page  # ceiling division

    if input.sort_by == "release_date":
        base_query = base_query.order_by(Movie.movie_id, Movie.release_date.desc())
    else:
        base_query = base_query.order_by(Movie.movie_id, Movie.rating.desc())

    base_query = base_query.distinct(Movie.movie_id)

    movies = (
        base_query
        .offset(offset)
        .limit(movies_per_page)
        .all()
    )

    if not movies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No movies found with the given filters"
        )

    movie_ids = [m.movie_id for m in movies]

    genres_for_movies = db.query(GenresToMovie).filter(GenresToMovie.movie_id.in_(movie_ids)).all()
    genres_map = {}
    for g in genres_for_movies:
        genres_map.setdefault(g.movie_id, []).append(g.genre_name)

    actors_for_movies = db.query(ActorToMovie).filter(ActorToMovie.movie_id.in_(movie_ids)).all()
    actors_map = {}
    for a in actors_for_movies:
        actors_map.setdefault(a.movie_id, []).append(a.actor_name)

    directors_for_movies = db.query(DirectorToMovie).filter(DirectorToMovie.movie_id.in_(movie_ids)).all()
    directors_map = {d.movie_id: d.director_name for d in directors_for_movies}

    results = []
    for movie in movies:
        results.append({
            "movie_id": movie.movie_id,
            "title": movie.title,
            "release_date": movie.release_date,
            "description": movie.description,
            "image_url": movie.image_url,
            "movie_length": movie.movie_length,
            "rating": movie.rating,
            "genres": genres_map.get(movie.movie_id, []),
            "actors": actors_map.get(movie.movie_id, []),
            "director": directors_map.get(movie.movie_id),
        })

    return {
        "results": results,
        "totalPages": total_pages
    }

    # return {
    #     "total_results": total_movies,
    #     "page": page,
    #     "results": results
    # }

@router.post("/actions",status_code=status.HTTP_201_CREATED)
def update_user_to_movie(input: UserToMovieModel, db: Session = Depends(get_db)):
    User = db.query(Users).filter(Users.user_id == input.user_id).first()
    movie = db.query(Movie).filter(Movie.movie_id == input.movie_id).first()
    if User is None or movie is None:
        raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Movie and/or User was not found"
            )
    if User.access_key != input.access_token:
            raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="This request is unauthorized"
                
            )
    if input.rating is not None and (input.rating < 0 or input.rating > 10):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 0 and 10"
        )
    relation = db.query(UserToMovie).filter(UserToMovie.user_id == input.user_id, UserToMovie.movie_id == input.movie_id).first()
    #if relation for user and movie exists update the status otherwise create it based on parameters given
    if not relation:
        relation = UserToMovie(
            user_id=input.user_id,
            movie_id=input.movie_id,
            has_watched = input.has_watched if input.has_watched is not None else False,
            times_watched = input.times_watched if input.times_watched is not None else 0,
            is_favorite = input.is_favorite if input.is_favorite is not None else False,
            watching_now = input.watching_now if input.watching_now is not None else False,
            rating = input.rating if input.rating is not None else 0

        )
        db.add(relation)
        db.commit()
        db.refresh(relation)

        return relation
    if input.times_watched is not None:
        relation.times_watched = input.times_watched
    if input.has_watched is not None:
        relation.has_watched = input.has_watched
    if input.is_favorite is not None:
        relation.is_favorite = input.is_favorite
    if input.watching_now is not None:
        relation.watching_now = input.watching_now
    if input.rating is not None:
        relation.rating = input.rating
    db.commit()
    db.refresh(relation)
    return relation

@router.get("/actions", status_code=status.HTTP_200_OK)
def get_user_to_movie_info(user_id:int , access_token: str, movie_id: int ,db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.user_id == user_id, Users.access_key == access_token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not exist or you are unauthorized",
        )
    movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie does not exist",
        )
    user_to_movie_info = db.query(UserToMovie).filter(UserToMovie.user_id == user_id, UserToMovie.movie_id == movie_id).first()
    if user_to_movie_info:
        return user_to_movie_info
    else:
        return {}

@router.get("/get_all_actions", status_code=status.HTTP_200_OK)
def get_all_user_movie_info(
    user_id: int,
    db: Session = Depends(get_db)
):
    # Authenticate the user
    user = db.query(Users).filter(
        Users.user_id == user_id,
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not exist or is unauthorized"
        )

    # Fetch all UserToMovie entries for the user and preload related Movie
    user_movie_entries = db.query(UserToMovie).filter(
    UserToMovie.user_id == user_id
    ).all()
    movie_ids = [entry.movie_id for entry in user_movie_entries]
    movies = db.query(Movie).options(
    joinedload(Movie.genres),
    joinedload(Movie.actors),
    joinedload(Movie.directors)
    ).filter(Movie.movie_id.in_(movie_ids)).all()
    movie_map = {movie.movie_id: movie for movie in movies}

    result = []
    for entry in user_movie_entries:
        movie = movie_map.get(entry.movie_id)
        if not movie:
            continue

        genre_names = [genre.genre_name for genre in movie.genres]
        actor_names = [actor.actor_name for actor in movie.actors]
        director_name = movie.directors[0].director_name if movie.directors else None

        result.append({
                "user_action": {
                    "has_watched": entry.has_watched,
                    "times_watched": entry.times_watched,
                    "is_favorite": entry.is_favorite,
                    "watching_now": entry.watching_now,
                    "rating": entry.rating,
                },
                "movie": {
                    "title": movie.title,
                    "description": movie.description,
                    "movie_length": movie.movie_length,
                    "rating": movie.rating,
                    "image_url": movie.image_url,
                    "movie_id": movie.movie_id,
                    "release_date": movie.release_date,
                    "director": director_name,
                    "genres": genre_names,
                    "actors": actor_names
                }
            })

    return result

@router.get("/get_movie_history",status_code=status.HTTP_200_OK, response_model=UserMovieInteraction)
def get_movie_history(user_id: int, access_key: str, db: Session = Depends(get_db)):
    if not check_valid_request(user_id, access_key, db):
        raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="This request is unauthorized or this user does not exist"
                )
    results = (
        db.query(UserToMovie, Movie)
        .join(Movie, UserToMovie.movie_id == Movie.movie_id)
        .filter(UserToMovie.user_id == user_id)
        .all()
        )

    favorite_movies = []
    movie_history = []
    most_watched_temp = []
    watching_now = []
    for utm, movie in results:
        if utm.times_watched > 0:
            most_watched_temp.append((movie, utm.times_watched))
        if utm.is_favorite:
            favorite_movies.append(movie)
        if utm.has_watched:
            movie_history.append(movie)
        if utm.watching_now:
            watching_now.append(movie)
    most_watched = [movie for movie, _ in sorted(most_watched_temp, key=lambda x: x[1], reverse=True)]
    return UserMovieInteraction(
        favorite_movies = favorite_movies,
        movie_history = movie_history,
        watching_now = watching_now,
        most_watched = most_watched,
    )

# def get_popular_suggested_movies( db: Session , genres: Optional[List[str]] = None):
#     six_months_ago = datetime.now() - timedelta(days=60)

#     query = db.query(Movie, func.sum(UserToMovie.times_watched).label("total_watched")).join(UserToMovie, Movie.movie_id == UserToMovie.movie_id).filter(Movie.release_date >= six_months_ago)
#     if genres:
#         query.filter(Movie.genres.in_(genres))
#     popular_movies = query.group_by(Movie.movie_id).order_by(func.sum(UserToMovie.times_watched).desc()).limit(8).all()
    
#     result = [movie for movie, total_watched in popular_movies]
#     return result

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

def get_popular_suggested_movies(db: Session, genres: Optional[List[str]] = None):
    #six_months_ago = datetime.now() - timedelta(days=180)  # 6 months

    #query = db.query(Movie).filter(Movie.release_date >= six_months_ago)
    query = db.query(Movie)
    if genres:
        # assuming you use a join table GenresToMovie for genre filtering
        genre_movie_ids = (
            db.query(GenresToMovie.movie_id)
            .filter(GenresToMovie.genre_name.in_(genres))
            .subquery()
        )
        query = query.filter(Movie.movie_id.in_(genre_movie_ids))

    # Order by rating descending instead of times_watched
    popular_movies = query.order_by(Movie.rating.desc()).limit(20).all()

    return popular_movies

def get_unreleased_movies(num:int, db: Session):
    today = datetime.now()
    unreleased_movies = (
        db.query(Movie)
        .filter(Movie.release_date > today)
        .order_by(Movie.release_date.asc())
        .limit(num)
        .all()
    )
    return unreleased_movies
# def get_popular_suggested_movies(db: Session, genres: Optional[List[str]] = None):
#     one_year_ago = datetime.now() - timedelta(days=365)

#     query = (
#         db.query(Movie)
#         .join(UserToMovie, Movie.movie_id == UserToMovie.movie_id)
#         .filter(Movie.release_date >= one_year_ago)
#         .filter(UserToMovie.is_favorite == True)
#     )

#     if genres:
#         genre_movie_ids = (
#             db.query(GenresToMovie.movie_id)
#             .filter(GenresToMovie.genre_name.in_(genres))
#             .subquery()
#         )
#         query = query.filter(Movie.movie_id.in_(genre_movie_ids))

#     popular_movies = (
#         query
#         .with_entities(Movie, func.count(UserToMovie.user_id).label("favorite_count"))
#         .group_by(Movie.movie_id)
#         .order_by(func.count(UserToMovie.user_id).desc())
#         .limit(20)
#         .all()
#     )

#     return [movie for movie, _ in popular_movies]


def get_recent_movies( db: Session):
    six_months_ago = datetime.now() - timedelta(days=180)
    new_movies = (
        db.query(Movie)
        .filter(Movie.release_date >= six_months_ago, Movie.release_date <= datetime.now())
        .order_by(Movie.rating.desc()).limit(20)
        .all()
    )
    return new_movies

@router.get("/landing_page_movies")
def get_landing_page_movies(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    result = {}
    result['popular_movies'] = get_popular_suggested_movies(db=db)
    result['new_movies'] = get_recent_movies(db=db)
    if (user_id):
        user = db.query(Users).filter(Users.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User does not exist",
            )
        try:
            result['recommended_movies'] = get_recommendation_eng_movies(user_id,1,20,db)
            result['collaborative_movies'] = get_recommendation_eng_movies(user_id,3,20,db=db)
        except Exception as e:
            result['recommended_movies'] = []
            result['collaborative_movies'] = []
    return result

@router.get("/get_movie_recommendation/{movie_id}")
def get_movie_watchlist_recommendations(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This movie does not exist"
        )
    try:
        recommended_movies = get_recommendation_eng_movies(movie_id,0,8,db)
    except Exception:
        recommended_movies = []
    return recommended_movies

# def delete_duplicate_movies(db: Session):
#     duplicates = (
#         db.query(Movie.title)
#         .group_by(Movie.title)
#         .having(func.count(Movie.movie_id) > 1)
#         .all()
#     )

#     for (title,) in duplicates:
#         movies = db.query(Movie).filter(Movie.title == title).order_by(Movie.movie_id).all()

#         movies_to_delete = movies[1:]

#         for movie in movies_to_delete:
#             db.query(GenresToMovie).filter(GenresToMovie.movie_id == movie.movie_id).delete()
#             db.query(ActorToMovie).filter(ActorToMovie.movie_id == movie.movie_id).delete()
#             db.query(DirectorToMovie).filter(DirectorToMovie.movie_id == movie.movie_id).delete()

#             db.delete(movie)

#     db.commit()

# @router.delete("/admin/delete-duplicate-movies")
# def delete_duplicate_movies_route(db: Session = Depends(get_db)):
#     delete_duplicate_movies(db)
#     return {"detail": "Duplicate movies deleted successfully"}


