import requests
from sqlalchemy.orm import Session,query
from models import Movie, GenresToMovie, DirectorToMovie, ActorToMovie
from database import get_db, initialize_database
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional, Tuple

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_API_URLS = [
    "https://api.themoviedb.org/3/movie/top_rated",
    "https://api.themoviedb.org/3/movie/popular",
    "https://api.themoviedb.org/3/movie/now_playing",
    "https://api.themoviedb.org/3/movie/upcoming"
]

def fetch_movies_from_tmdb(start_date: Optional[str] = None, end_date: Optional[str] = None):
    """
    Fetch movies from TMDB API with optional date range filtering
    
    Args:
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
    """
    movies = {}

    for url in TMDB_API_URLS:
        for page in range(1, 500):  
            try:
                params = {
                    "api_key": TMDB_API_KEY, 
                    "language": "en-US", 
                    "page": page
                }
                
                # Add date filters if using discover endpoint
                if "discover" in url:
                    if start_date:
                        params["primary_release_date.gte"] = start_date
                    if end_date:
                        params["primary_release_date.lte"] = end_date
                
                response = requests.get(url, params=params)
                response.raise_for_status()
                movies_data = response.json()
                
                for movie in movies_data.get("results", []):
                    # Apply date filtering for non-discover endpoints
                    if start_date or end_date:
                        release_date = movie.get("release_date")
                        if release_date:
                            if start_date and release_date < start_date:
                                continue
                            if end_date and release_date > end_date:
                                continue
                    
                    movies[movie["id"]] = movie  
                    print(f"Found movie: {movie.get('title')} ({movie.get('release_date')})")
                
            except requests.RequestException as e:
                print(f"Error fetching page {page} from TMDb: {e}")
                break 
                
    return list(movies.values())

def fetch_movies_by_date_range(start_date: str, end_date: str):
    """
    Fetch movies using the discover endpoint with date range
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    movies = {}
    discover_url = "https://api.themoviedb.org/3/discover/movie"
    
    for page in range(1, 500):
        try:
            params = {
                "api_key": TMDB_API_KEY,
                "language": "en-US",
                "page": page,
                "primary_release_date.gte": start_date,
                "primary_release_date.lte": end_date,
                "sort_by": "popularity.desc"
            }
            
            response = requests.get(discover_url, params=params)
            response.raise_for_status()
            movies_data = response.json()
            
            if not movies_data.get("results"):
                break
                
            for movie in movies_data.get("results", []):
                movies[movie["id"]] = movie
                print(f"Found movie: {movie.get('title')} ({movie.get('release_date')})")
                
        except requests.RequestException as e:
            print(f"Error fetching page {page} from TMDb discover: {e}")
            break
            
    return list(movies.values())

def fetch_movie_details(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    try:
        response = requests.get(url, params={"api_key": TMDB_API_KEY, "language": "en-US"})
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching details for movie ID {movie_id}: {e}")
        return None

def fetch_director_name(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits"
    try:
        response = requests.get(url, params={"api_key": TMDB_API_KEY})
        response.raise_for_status()
        credits = response.json()
        for person in credits.get("crew", []):
            if person.get("job") == "Director":
                return person.get("name")
    except requests.RequestException as e:
        print(f"Error fetching director for movie ID {movie_id}: {e}")
    return None

def fetch_actor_names(movie_id, max_actors=5):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits"
    try:
        response = requests.get(url, params={"api_key": TMDB_API_KEY})
        response.raise_for_status()
        credits = response.json()
        actor_names = [person.get("name") for person in credits.get("cast", [])[:max_actors]]
        return actor_names
    except requests.RequestException as e:
        print(f"Error fetching actors for movie ID {movie_id}: {e}")
        return []

def update_movie_info(db: Session, movie_id: int):
    """
    Update existing movie information from TMDB
    
    Args:
        db: Database session
        movie_id: TMDB movie ID
    """
    try:
        # Find existing movie in database
        existing_movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
        if not existing_movie:
            print(f"Movie with TMDB ID {movie_id} not found in database")
            return False
        
        # Fetch updated details from TMDB
        movie_details = fetch_movie_details(movie_id)
        if not movie_details:
            print(f"Could not fetch updated details for movie ID {movie_id}")
            return False
        
        # Update movie fields
        old_rating = existing_movie.rating
        new_rating = movie_details.get("vote_average")
        
        existing_movie.rating = new_rating
        existing_movie.description = movie_details.get("overview")
        existing_movie.movie_length = movie_details.get("runtime") or existing_movie.movie_length
        
        # Update image URL if available
        if movie_details.get("poster_path"):
            existing_movie.image_url = f"https://image.tmdb.org/t/p/w500{movie_details.get('poster_path')}"
        
        db.commit()
        print(f"Updated movie '{existing_movie.title}': Rating {old_rating} -> {new_rating}")
        return True
        
    except Exception as e:
        print(f"Error updating movie ID {movie_id}: {e}")
        db.rollback()
        return False

def update_all_movies(db: Session):
    """
    Update all movies in the database with latest TMDB information
    """
    movies = db.query(Movie).all()
    updated_count = 0
    
    for movie in movies:
        # Note: This assumes you have a tmdb_id field or can derive it
        # You may need to modify this based on your Movie model
        if hasattr(movie, 'tmdb_id'):
            if update_movie_info(db, movie.tmdb_id):
                updated_count += 1
        else:
            print(f"Warning: Movie '{movie.title}' doesn't have TMDB ID for updating")
    
    print(f"Updated {updated_count} movies")

def populate_movies(db: Session, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """
    Populate database with movies, optionally filtered by date range
    
    Args:
        db: Database session
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
    """
    if start_date and end_date:
        print(f"Fetching movies from {start_date} to {end_date}")
        movies = fetch_movies_by_date_range(start_date, end_date)
    elif start_date or end_date:
        print(f"Fetching movies with date filter: {start_date or 'any'} to {end_date or 'any'}")
        movies = fetch_movies_from_tmdb(start_date, end_date)
    else:
        print("Fetching all movies (no date filter)")
        movies = fetch_movies_from_tmdb()
    
    added_count = 0
    skipped_count = 0
    
    for movie_data in movies:
        try:
            movie_id = movie_data.get("id")
            title = movie_data.get("title")
            if not movie_id or not title:
                continue
            
            # Skip duplicate movies
            existing_movie = db.query(Movie).filter(Movie.title == title).first()
            if existing_movie:
                print(f"Movie '{title}' already exists. Skipping.")
                skipped_count += 1
                continue
            
            movie_details = fetch_movie_details(movie_id)
            if not movie_details:
                continue
            
            description = movie_details.get("overview")
            release_date_str = movie_details.get("release_date")
            
            # Ensure release_date is parsed correctly
            try:
                release_date = datetime.strptime(release_date_str, "%Y-%m-%d") if release_date_str else None
            except ValueError as e:
                print(f"Error parsing release date for movie '{title}': {e}")
                release_date = None

            rating = movie_details.get("vote_average")
            movie_length = movie_details.get("runtime") or 120
            image_url = f"https://image.tmdb.org/t/p/w500{movie_details.get('poster_path')}" if movie_details.get("poster_path") else None

            new_movie = Movie(
                title=title,
                description=description,
                movie_length=movie_length,
                rating=rating,
                image_url=image_url,
                release_date=release_date
            )
            db.add(new_movie)
            db.commit()
            db.refresh(new_movie)

            # Add genres
            genres = movie_details.get("genres", [])
            for genre in genres:
                genre_name = genre.get("name")
                if genre_name:
                    genre_to_movie = GenresToMovie(movie_id=new_movie.movie_id, genre_name=genre_name)
                    db.add(genre_to_movie)

            # Add director
            director_name = fetch_director_name(movie_id)
            if director_name:
                director_to_movie = DirectorToMovie(movie_id=new_movie.movie_id, director_name=director_name)
                db.add(director_to_movie)
            
            # Add actors
            actors = fetch_actor_names(movie_id)
            for actor_name in actors:
                if actor_name:
                    actor_to_movie = ActorToMovie(movie_id=new_movie.movie_id, actor_name=actor_name)
                    db.add(actor_to_movie)
            
            db.commit()
            added_count += 1
            print(f"Added movie '{title}' ({release_date_str}) to database")
            
        except Exception as e:
            print(f"Error processing movie '{title}': {e}")
            db.rollback()
            continue
    
    print(f"Database population complete: {added_count} movies added, {skipped_count} skipped")

if __name__ == "__main__":
    db = next(get_db()) 
    
    try:
        # Example usage with date range (modify as needed)
        start_date = "2023-01-01"  # Change this to your desired start date
        end_date = "2024-12-31"    # Change this to your desired end date
        
        # Populate with date range
        populate_movies(db, start_date, end_date)
        
        # Or populate without date range (comment out the line above and uncomment below)
        # populate_movies(db)
        
        # Update existing movies (uncomment if needed)
        # update_all_movies(db)
        
    finally:
        db.close()