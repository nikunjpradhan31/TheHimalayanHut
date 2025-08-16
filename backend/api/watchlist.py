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
from .recommendations import get_recommendation_eng_movies
router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.post("/create", response_model=WatchListResponse, status_code=status.HTTP_201_CREATED)
def create_watchlist(input: WatchListCreate, db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.user_id == input.owner).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not logged in or this account does not exist"
        )
    print(user.access_key, input.access_token)
    if user.access_key != input.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )
    output = WatchList(
        watchlist_title= input.watchlist_title,
        owner = input.owner,
        number_of_movies= 0,
        created_at= datetime.now(),
        )
    db.add(output)
    db.commit()
    db.refresh(output)
    return output

@router.get("/get_all/{user_id}/{access_token}", response_model=AllWatchListResponse)
def Get_All_WatchLists(user_id: int,access_token: str, db: Session = Depends(get_db)):
    
    user = db.query(Users).filter(Users.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not logged in or this account does not exist"
        )
    if user.access_key != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )
    watchlists = db.query(WatchList).filter(WatchList.owner == user_id).all()
    if not watchlists:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT , detail="No watchlists found for this user")
    
    watchlists_data = [
        WatchListResponse(
            watchlist_id=watchlist.watchlist_id,
            watchlist_title=watchlist.watchlist_title,
            number_of_movies=watchlist.number_of_movies,
            created_at=watchlist.created_at,
            owner=watchlist.owner,
        )
        for watchlist in watchlists
    ]
    return AllWatchListResponse(watchlists=watchlists_data)

@router.get("/get/{watchlist_id}", response_model=WatchListResponse)
def get_watchlist(watchlist_id: int, db: Session = Depends(get_db)):
    
    watchlist = db.query(WatchList).filter(WatchList.watchlist_id == watchlist_id).first()
    if not watchlist:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT , detail="No watchlist found for this id")
    
    watchlist_data = WatchListResponse(
            watchlist_id=watchlist.watchlist_id,
            watchlist_title=watchlist.watchlist_title,
            number_of_movies=watchlist.number_of_movies,
            created_at=watchlist.created_at,
            owner=watchlist.owner,
        )

    return watchlist_data

@router.post("/add_movie", response_model=MoviesInWatchListResponse, status_code=status.HTTP_201_CREATED)
def add_movie(input: MoviesInWatchListCreate, db: Session = Depends(get_db)):

    watchlist = db.query(WatchList).filter(WatchList.watchlist_id == input.watchlist_id).first()
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This watchlist does not exist"
        )
    user = db.query(Users).filter(Users.user_id == input.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not logged in or this account does not exist"
        )

    # Check if user is owner
    is_owner = watchlist.owner == input.user_id

    # Check if user is guest with EDITOR role
    user_guest_relationship = db.query(GuestToWatchlists).filter(
        GuestToWatchlists.user_id == input.user_id,
        GuestToWatchlists.watchlist_id == watchlist.watchlist_id,
        GuestToWatchlists.role == "EDITOR"
    ).first()

    if not is_owner and not user_guest_relationship:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to perform this action"
        )

    # Validate access token
    if user.access_key != input.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        )

    movie = db.query(Movie).filter(Movie.movie_id == input.movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This movie does not exist"
        )
    
    IsMovieInWatchList =  db.query(MoviesInWatchList).filter(MoviesInWatchList.movie_id == input.movie_id,MoviesInWatchList.watchlist_id == input.watchlist_id,).first()
    if IsMovieInWatchList:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail="This movie is already in the watchlist"
        )
    
    db_MIW = MoviesInWatchList(
        watchlist_id = input.watchlist_id,
        movie_id = input.movie_id
    )
    db.add(db_MIW)
    watchlist.number_of_movies += 1
    db.commit()
    return db_MIW    

@router.delete("/delete_movie/{user_id}/{watchlist_id}/{movie_id}/{access_token}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movie(user_id: int, watchlist_id: int, movie_id: int,access_token: str, db: Session = Depends(get_db)):
    watchlist = db.query(WatchList).filter(WatchList.watchlist_id == watchlist_id).first()
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This watchlist does not exist"
        )
    user = db.query(Users).filter(Users.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not logged in or this account does not exist"
        )

    # Check if user is owner
    is_owner = watchlist.owner == user_id

    # Check if user is guest with EDITOR role
    user_guest_relationship = db.query(GuestToWatchlists).filter(
        GuestToWatchlists.user_id == user_id,
        GuestToWatchlists.watchlist_id == watchlist.watchlist_id,
        GuestToWatchlists.role == "EDITOR"
    ).first()

    if not is_owner and not user_guest_relationship:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to perform this action"
        )

    # Validate access token
    if user.access_key != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        )
    IsMovieInWatchList = db.query(MoviesInWatchList).filter(MoviesInWatchList.movie_id == movie_id, MoviesInWatchList.watchlist_id == watchlist_id).first()
    if not IsMovieInWatchList:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This movie is not in the watchlist"
        )
    db.delete(IsMovieInWatchList)
    watchlist.number_of_movies -= 1
    db.commit()
    return

@router.delete("/delete/{watchlist_id}/{access_token}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist(watchlist_id: int,access_token:str, db: Session = Depends(get_db)):
    watchlist = db.query(WatchList).filter(WatchList.watchlist_id == watchlist_id).first()
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This watchlist does not exist"
        )
    user = db.query(Users).filter(Users.user_id == watchlist.owner).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account does not exist or you are not logged in"
        )
    if user.access_key != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )
    db.query(GuestToWatchlists).filter(GuestToWatchlists.watchlist_id == watchlist_id).delete()

    db.delete(watchlist)
    db.commit()
    return

@router.get("/get_movies/{watchlist_id}", response_model=AllMoviesInWatchResponse)
def Get_All_Movies_In_WatchList(watchlist_id: int, db: Session = Depends(get_db)):
    watchlist = db.query(WatchList).filter(WatchList.watchlist_id == watchlist_id).first()
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This watchlist does not exist"
        )
    
    moviesInWatchListID = db.query(MoviesInWatchList).filter(MoviesInWatchList.watchlist_id == watchlist_id).all()
    movie_ids = [entry.movie_id for entry in moviesInWatchListID]

    movies = (
        db.query(Movie)
        .options(
            joinedload(Movie.genres),
            joinedload(Movie.actors),
            joinedload(Movie.directors)
        )
        .filter(Movie.movie_id.in_(movie_ids))
        .all()
    )

    if not movies:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="No movies were found")

    movies_data = []
    for movie in movies:
        movies_data.append(
            MovieResponse(
                title=movie.title,
                description=movie.description,
                movie_length=movie.movie_length,
                rating=movie.rating,
                image_url=movie.image_url,
                movie_id=movie.movie_id,
                release_date=movie.release_date,
                director=movie.directors[0].director_name if movie.directors else None,
                genres=[genre.genre_name for genre in movie.genres],
                actors=[actor.actor_name for actor in movie.actors]
            )
        )

    return AllMoviesInWatchResponse(movies=movies_data)


@router.get("/get_movie_recommendation/{watchlist_id}")
def get_movie_watchlist_recommendations(watchlist_id: int, db: Session = Depends(get_db)):
    watchlist = db.query(WatchList).filter(WatchList.watchlist_id == watchlist_id).first()
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This watchlist does not exist"
        )
    try:
        recommended_movies = get_recommendation_eng_movies(watchlist_id,2,7,db)
    except Exception: 
        recommended_movies = []
    return recommended_movies

@router.put("/update", response_model=WatchListResponse, status_code=status.HTTP_202_ACCEPTED)
def update_Watchlist(input: WatchListUpdate, db: Session = Depends(get_db)):
    watchlist = db.query(WatchList).filter(WatchList.watchlist_id == input.watchlist_id, Users.user_id == input.owner).first()
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This watchlist does not exist"
        )
    user = db.query(Users).filter(Users.user_id == watchlist.owner).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account does not exist or you are not logged in"
        )
    if user.access_key != input.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )
    watchlist.watchlist_title = input.watchlist_title
    db.commit()
    db.refresh(watchlist)
    return watchlist

@router.get("/get_all_guests_watchlists/{user_id}/{access_token}", response_model=AllWatchListResponse,status_code=status.HTTP_200_OK)
def get_all_guest_watchlists(user_id: int,access_token:str, db: Session = Depends(get_db)):
    
    user = db.query(Users).filter(Users.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not logged in or this account does not exist"
        )
    if user.access_key != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )
    
    watchlists = (
    db.query(WatchList, GuestToWatchlists.role)
    .join(GuestToWatchlists, GuestToWatchlists.watchlist_id == WatchList.watchlist_id)
    .filter(GuestToWatchlists.user_id == user_id)
    .all()
)

    if not watchlists:
        raise HTTPException(status_code=204, detail="No watchlists are found where you are a guest")
    
    watchlists_data = [
        WatchListResponse(
            watchlist_id=watchlist.watchlist_id,
            watchlist_title=watchlist.watchlist_title,
            number_of_movies=watchlist.number_of_movies,
            created_at=watchlist.created_at,
            owner=watchlist.owner,
            role = role.name.title()
        )
        
        for watchlist, role in watchlists
    ]
    return AllWatchListResponse(watchlists=watchlists_data)

@router.post("/add_guest", response_model=GuestToWatchlistsResponse, status_code=status.HTTP_201_CREATED)
def add_guest_to_watchlist(input: GuestToWatchlistsCreate, db: Session = Depends(get_db)):

    watchlist = db.query(WatchList).filter(WatchList.watchlist_id == input.watchlist_id).first()
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found"
        )
    user = db.query(Users).filter(Users.user_id == watchlist.owner).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not exist",
        )
    if user.access_key != input.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )
    guest = db.query(Users).filter(Users.user_id == input.user_id).first()
    if not guest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    existing_guest = db.query(GuestToWatchlists).filter(
        GuestToWatchlists.watchlist_id == input.watchlist_id,
        GuestToWatchlists.user_id == input.user_id
    ).first()

    if existing_guest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is already a guest in the watchlist"
        )

    new_guest = GuestToWatchlists(
        watchlist_id=input.watchlist_id,
        user_id=input.user_id,
        invited_at=datetime.now(),
        role=input.role,
    )
    db.add(new_guest)
    db.commit()
    db.refresh(new_guest)

    return GuestToWatchlistsResponse(
        watchlist_id=new_guest.watchlist_id,
        user_id=new_guest.user_id,
        invited_at=new_guest.invited_at,
        role=str(new_guest.role.value),
        username=guest.username
    )

@router.delete("/remove_guest/{watchlist_id}/{user_id}/{access_token}", status_code=status.HTTP_204_NO_CONTENT)
def remove_guest_from_watchlist(watchlist_id: int, user_id: int,access_token:str, db: Session = Depends(get_db)):
    watchlist = db.query(WatchList).filter(WatchList.watchlist_id == watchlist_id).first()
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found"
        )
    user = db.query(Users).filter(Users.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not exist",
        )
    owner = db.query(Users).filter(Users.user_id == watchlist.owner).first()

    if owner.access_key != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )
    
    guest = db.query(GuestToWatchlists).filter(
        GuestToWatchlists.watchlist_id == watchlist_id,
        GuestToWatchlists.user_id == user_id
    ).first()

    if not guest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The guest is not part of this watchlist"
        )
    db.delete(guest)
    db.commit()
    return

@router.get("/search/{substring}/{user_id}", response_model=AllWatchListResponse, status_code=status.HTTP_200_OK)
def search_watchlists(substring: str, user_id: int, db: Session = Depends(get_db)):
    watchlists = db.query(WatchList).filter(
        WatchList.watchlist_title.ilike(f"%{substring}%"),
        WatchList.owner != user_id
    ).all()
    
    if not watchlists:
        raise HTTPException(status_code=204, detail="No public watchlists found matching the search criteria.")
    
    return AllWatchListResponse(watchlists=watchlists)

@router.get("/all_guests/{watchlist_id}", response_model=GuestToWatchlistsResponseList, status_code=status.HTTP_200_OK)
def get_all_guests(watchlist_id: int, db: Session = Depends(get_db)):
    watchlist = db.query(WatchList).filter(WatchList.watchlist_id == watchlist_id).first()
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This watchlist does not exist"
        )
    guests_with_details = (
        db.query(GuestToWatchlists, Users)
        .join(Users, GuestToWatchlists.user_id == Users.user_id)
        .filter(GuestToWatchlists.watchlist_id == watchlist_id)
        .all()
    )

    if not guests_with_details:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail="You have no current guests in this watchlist"
        )
    guests = GuestToWatchlistsResponseList(
        guests=[
            GuestToWatchlistsResponse(
                username=user.username,
                user_id=guest.user_id,
                role=str(guest.role.value),
                invited_at=guest.invited_at,
                watchlist_id = guest.watchlist_id,
            )
            for guest, user in guests_with_details
        ]
    )
    return guests

@router.post("/update_guest", response_model=GuestToWatchlistsResponse, status_code=status.HTTP_201_CREATED)
def update_guest_permissions(input: GuestToWatchlistsCreate, db: Session = Depends(get_db)):

    watchlist = db.query(WatchList).filter(WatchList.watchlist_id == input.watchlist_id).first()
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found"
        )
    user = db.query(Users).filter(Users.user_id == watchlist.owner).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not exist",
        )
    if user.access_key != input.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )
    guest = db.query(Users).filter(Users.user_id == input.user_id).first()
    if not guest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    existing_guest = db.query(GuestToWatchlists).filter(
        GuestToWatchlists.watchlist_id == input.watchlist_id,
        GuestToWatchlists.user_id == input.user_id
    ).first()

    if not existing_guest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is not a guest in the watchlist"
        )
    existing_guest.role = input.role
    db.commit()
    db.refresh(existing_guest)

    return GuestToWatchlistsResponse(
        watchlist_id=existing_guest.watchlist_id,
        user_id=existing_guest.user_id,
        invited_at=existing_guest.invited_at,
        role=existing_guest.role.value,
        username = guest.username,
    )
