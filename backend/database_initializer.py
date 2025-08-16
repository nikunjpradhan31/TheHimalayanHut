import requests
from sqlalchemy.orm import Session
from models import Movie, GenresToMovie, DirectorToMovie, ActorToMovie
from database import get_db, initialize_database
import os
from dotenv import load_dotenv
from datetime import datetime
import time
from typing import List, Dict, Set
import logging

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_init.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TMDB_API_KEY = os.getenv("TMDB_API_KEY")

class DatabaseInitializer:
    def __init__(self):
        if not TMDB_API_KEY:
            raise ValueError("TMDB_API_KEY not found in environment variables")
        
        self.api_key = TMDB_API_KEY
        self.base_url = "https://api.themoviedb.org/3"
        self.session = requests.Session()
        self.processed_movies = set()
        
    def make_request(self, url: str, params: dict = None, retries: int = 3) -> dict:
        """Make API request with retry logic and rate limiting"""
        if params is None:
            params = {}
        
        params["api_key"] = self.api_key
        params["language"] = "en-US"
        
        for attempt in range(retries):
            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                time.sleep(0.25) 
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
        
    def fetch_popular_movies_by_year(self, year: int, max_pages: int = 5) -> List[Dict]:
        """Fetch popular movies for a specific year"""
        movies = []
        
        for page in range(1, max_pages + 1):
            try:
                url = f"{self.base_url}/discover/movie"
                params = {
                    "primary_release_year": year,
                    "sort_by": "popularity.desc",
                    "page": page,
                    "vote_count.gte": 10  
                }
                
                data = self.make_request(url, params)
                
                if not data.get("results"):
                    break
                    
                movies.extend(data["results"])
                
                # Log progress
                if page % 2 == 0:
                    logger.info(f"Fetched page {page} for year {year} - {len(movies)} movies so far")
                    
            except Exception as e:
                logger.error(f"Error fetching popular movies for year {year}, page {page}: {e}")
                break
        
        return movies
    
    def fetch_top_rated_movies_by_year(self, year: int, max_pages: int = 5) -> List[Dict]:
        """Fetch top-rated movies for a specific year"""
        movies = []
        
        for page in range(1, max_pages + 1):
            try:
                url = f"{self.base_url}/discover/movie"
                params = {
                    "primary_release_year": year,
                    "sort_by": "vote_average.desc",
                    "page": page,
                    "vote_count.gte": 10,  
                    "vote_average.gte": 3.0 
                }
                
                data = self.make_request(url, params)
                
                if not data.get("results"):
                    break
                    
                movies.extend(data["results"])
            
                if page % 2 == 0:
                    logger.info(f"Fetched page {page} top-rated for year {year} - {len(movies)} movies so far")
                    
            except Exception as e:
                logger.error(f"Error fetching top-rated movies for year {year}, page {page}: {e}")
                break
        
        return movies
    
    def fetch_movie_details(self, movie_id: int) -> dict:
        """Fetch detailed information for a specific movie"""
        try:
            url = f"{self.base_url}/movie/{movie_id}"
            return self.make_request(url)
        except Exception as e:
            logger.error(f"Error fetching details for movie ID {movie_id}: {e}")
            return None
    
    def fetch_movie_credits(self, movie_id: int) -> dict:
        """Fetch credits (cast and crew) for a specific movie"""
        try:
            url = f"{self.base_url}/movie/{movie_id}/credits"
            return self.make_request(url)
        except Exception as e:
            logger.error(f"Error fetching credits for movie ID {movie_id}: {e}")
            return None
    
    def get_director_from_credits(self, credits: dict) -> str:
        """Extract director name from credits"""
        if not credits:
            return None
            
        for person in credits.get("crew", []):
            if person.get("job") == "Director":
                return person.get("name")
        return None
    
    def get_actors_from_credits(self, credits: dict, max_actors: int = 5) -> List[str]:
        """Extract actor names from credits"""
        if not credits:
            return []
            
        actors = []
        for person in credits.get("cast", [])[:max_actors]:
            if person.get("name"):
                actors.append(person.get("name"))
        return actors
    
    def save_movie_to_db(self, movie_data: dict, db: Session) -> bool:
        """Save a movie and its related data to the database"""
        try:
            movie_id = movie_data.get("id")
            title = movie_data.get("title")
            
            if not movie_id or not title:
                return False
            
            # Check if movie already exists
            existing_movie = db.query(Movie).filter(Movie.title == title).first()
            if existing_movie:
                logger.debug(f"Movie '{title}' already exists, skipping")
                return False
            
            # Get detailed movie information
            movie_details = self.fetch_movie_details(movie_id)
            if not movie_details:
                return False
            
            # Parse release date
            release_date_str = movie_details.get("release_date")
            try:
                release_date = datetime.strptime(release_date_str, "%Y-%m-%d") if release_date_str else None
            except ValueError:
                release_date = None
            
            # Create movie record
            new_movie = Movie(
                title=title,
                description=movie_details.get("overview"),
                movie_length=movie_details.get("runtime") or 120,
                rating=movie_details.get("vote_average"),
                image_url=f"https://image.tmdb.org/t/p/w500{movie_details.get('poster_path')}" if movie_details.get("poster_path") else None,
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
                    genre_to_movie = GenresToMovie(
                        movie_id=new_movie.movie_id, 
                        genre_name=genre_name
                    )
                    db.add(genre_to_movie)
            
            # Get and add credits
            credits = self.fetch_movie_credits(movie_id)
            
            # Add director
            director_name = self.get_director_from_credits(credits)
            if director_name:
                director_to_movie = DirectorToMovie(
                    movie_id=new_movie.movie_id,
                    director_name=director_name
                )
                db.add(director_to_movie)
            
            # Add actors
            actor_names = self.get_actors_from_credits(credits)
            for actor_name in actor_names:
                actor_to_movie = ActorToMovie(
                    movie_id=new_movie.movie_id,
                    actor_name=actor_name
                )
                db.add(actor_to_movie)
            
            db.commit()
            logger.info(f"Successfully added movie: '{title}' ({release_date_str})")
            return True
            
        except Exception as e:
            logger.error(f"Error saving movie '{title}': {e}")
            db.rollback()
            return False
    
    def initialize_database_1980_present(self, db: Session):
        """Initialize database with movies from 1980 to present"""
        current_year = datetime.now().year
        start_year = 1970
        
        total_movies_added = 0
        total_movies_processed = 0
        
        logger.info(f"Starting database initialization from {start_year} to {current_year}")
        logger.info("This process may take several hours due to API rate limits...")
        
        for year in range(start_year, current_year + 1):
            year_start_time = time.time()
            year_movies_added = 0
            
            logger.info(f"\n=== Processing year {year} ===")
            
            logger.info(f"Fetching popular movies for {year}...")
            popular_movies = self.fetch_popular_movies_by_year(year)
            
            logger.info(f"Fetching top-rated movies for {year}...")
            top_rated_movies = self.fetch_top_rated_movies_by_year(year)
            
            all_movies = {movie["id"]: movie for movie in popular_movies + top_rated_movies}
            unique_movies = list(all_movies.values())
            
            logger.info(f"Found {len(unique_movies)} unique movies for {year}")
            
            for movie_data in unique_movies:
                total_movies_processed += 1
                
                if self.save_movie_to_db(movie_data, db):
                    total_movies_added += 1
                    year_movies_added += 1
                
                if total_movies_processed % 10 == 0:
                    logger.info(f"Progress: {total_movies_processed} movies processed, {total_movies_added} added")
            
            year_duration = time.time() - year_start_time
            logger.info(f"Year {year} completed: {year_movies_added} movies added in {year_duration:.1f} seconds")
            
            time.sleep(1)
        
        logger.info(f"\n=== Database Initialization Complete ===")
        logger.info(f"Total movies processed: {total_movies_processed}")
        logger.info(f"Total movies added: {total_movies_added}")
        logger.info(f"Years covered: {start_year} to {current_year}")
    
    def initialize_database_quick(self, db: Session, max_movies_per_year: int = 1000):
        """Quick initialization with limited movies per year (for testing)"""
        current_year = datetime.now().year
        start_year = 2020  
        
        logger.info(f"Quick initialization from {start_year} to {current_year} ({max_movies_per_year} movies per year)")
        
        total_added = 0
        
        for year in range(start_year, current_year + 1):
            logger.info(f"Processing year {year}...")
            
            # Get top movies for this year
            movies = self.fetch_popular_movies_by_year(year, max_pages=4)
            
            # Limit movies per year
            movies = movies[:max_movies_per_year]
            
            year_added = 0
            for movie_data in movies:
                if self.save_movie_to_db(movie_data, db):
                    year_added += 1
                    total_added += 1
            
            logger.info(f"Year {year}: {year_added} movies added")
        
        logger.info(f"Quick initialization complete: {total_added} movies added")

async def run_full_initialization():
    """Run full database initialization"""
    logger.info("Starting full database initialization (1980-present)")
    
    await initialize_database()
    
    initializer = DatabaseInitializer()
    
    db = next(get_db())
    
    try:
        initializer.initialize_database_1980_present(db)
    except KeyboardInterrupt:
        logger.info("Initialization interrupted by user")
    except Exception as e:
        logger.error(f"Error during initialization: {e}")
    finally:
        db.close()

async def run_quick_initialization():
    """Run quick database initialization (for testing)"""
    logger.info("Starting quick database initialization (recent years)")
    
    await initialize_database()
    
    initializer = DatabaseInitializer()
    
    db = next(get_db())
    
    try:
        initializer.initialize_database_quick(db)
    except Exception as e:
        logger.error(f"Error during quick initialization: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import asyncio
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize Movie Database")
    parser.add_argument("--mode", choices=["full", "quick"], default="quick",
                       help="Initialization mode: 'full' for 1980-present, 'quick' for recent years")
    
    args = parser.parse_args()
    
    if args.mode == "full":
        asyncio.run(run_full_initialization())
    else:
        asyncio.run(run_quick_initialization())
