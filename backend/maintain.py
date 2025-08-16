import schedule
import time
import logging
from datetime import datetime, timedelta
from threading import Thread
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import get_db, initialize_database
from models import Movie, GenresToMovie, DirectorToMovie, ActorToMovie
import requests
from typing import Optional
# Import functions from your populator script
# Assuming the enhanced populator code is in a file called movie_populator.py
try:
    from populate_database import (
        populate_movies, 
        # update_all_movies, 
        # fetch_movies_by_date_range,
        update_movie_info
    )
except ImportError:
    print("Warning: Could not import movie_populator functions. Make sure the file exists.")

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('maintenance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MovieMaintenance:
    def __init__(self):
        self.tmdb_api_key = os.getenv("TMDB_API_KEY")
        if not self.tmdb_api_key:
            raise ValueError("TMDB_API_KEY not found in environment variables")
    
    def get_db_session(self) -> Session:
        """Get database session"""
        return next(get_db())
    
    def weekly_movie_update(self):
        """Update existing movies with latest information from TMDB"""
        logger.info("Starting weekly movie update task...")
        
        db = self.get_db_session()
        try:
            # Update all existing movies
            movies = db.query(Movie).all()
            updated_count = 0
            failed_count = 0
            
            for movie in movies:
                try:
                    # If you have TMDB ID stored, use it; otherwise skip
                    if hasattr(movie, 'tmdb_id') and movie.tmdb_id:
                        if update_movie_info(db, movie.tmdb_id):
                            updated_count += 1
                        else:
                            failed_count += 1
                    else:
                        logger.warning(f"Movie '{movie.title}' has no TMDB ID for updating")
                        
                except Exception as e:
                    logger.error(f"Error updating movie '{movie.title}': {e}")
                    failed_count += 1
                    continue
            
            logger.info(f"Weekly update completed: {updated_count} movies updated, {failed_count} failed")
            
        except Exception as e:
            logger.error(f"Error during weekly movie update: {e}")
        finally:
            db.close()
    
    def weekly_new_movies(self):
        """Fetch new movies from the past week"""
        logger.info("Starting weekly new movies fetch task...")
        
        db = self.get_db_session()
        try:
            # Get date range for the past week
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)
            
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            logger.info(f"Fetching movies released between {start_date_str} and {end_date_str}")
            
            # Populate with new movies from the past week
            populate_movies(db, start_date_str, end_date_str)
            
            logger.info("Weekly new movies fetch completed")
            
        except Exception as e:
            logger.error(f"Error during weekly new movies fetch: {e}")
        finally:
            db.close()
    
    def monthly_popular_movies(self):
        """Fetch popular and trending movies monthly"""
        logger.info("Starting monthly popular movies fetch task...")
        
        db = self.get_db_session()
        try:
            # Get date range for the past month
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            logger.info(f"Fetching popular movies from {start_date_str} to {end_date_str}")
            
            # Populate with movies from the past month
            populate_movies(db, start_date_str, end_date_str)
            
            logger.info("Monthly popular movies fetch completed")
            
        except Exception as e:
            logger.error(f"Error during monthly popular movies fetch: {e}")
        finally:
            db.close()
    
    def cleanup_old_data(self):
        """Clean up old or duplicate data (optional maintenance)"""
        logger.info("Starting database cleanup task...")
        
        db = self.get_db_session()
        try:
            # Example: Remove movies with no ratings after 30 days
            cutoff_date = datetime.now() - timedelta(days=30)
            
            old_movies = db.query(Movie).filter(
                Movie.rating == None,
                Movie.release_date < cutoff_date
            ).all()
            
            removed_count = 0
            for movie in old_movies:
                # Remove related records first
                db.query(GenresToMovie).filter(GenresToMovie.movie_id == movie.movie_id).delete()
                db.query(DirectorToMovie).filter(DirectorToMovie.movie_id == movie.movie_id).delete()
                db.query(ActorToMovie).filter(ActorToMovie.movie_id == movie.movie_id).delete()
                
                # Remove the movie
                db.delete(movie)
                removed_count += 1
            
            db.commit()
            logger.info(f"Cleanup completed: {removed_count} old movies removed")
            
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
            db.rollback()
        finally:
            db.close()
    
    def health_check(self):
        """Perform basic health check on the database"""
        logger.info("Performing database health check...")
        
        db = self.get_db_session()
        try:
            # Count movies
            movie_count = db.query(Movie).count()
            
            # Count movies added in the last week
            week_ago = datetime.now() - timedelta(days=7)
            recent_movies = db.query(Movie).filter(Movie.release_date >= week_ago).count()
            
            # Count movies without ratings
            movies_no_rating = db.query(Movie).filter(Movie.rating == None).count()
            
            logger.info(f"Health Check Results:")
            logger.info(f"  Total movies: {movie_count}")
            logger.info(f"  Movies added this week: {recent_movies}")
            logger.info(f"  Movies without ratings: {movies_no_rating}")
            
            # Alert if no movies were added recently
            if recent_movies == 0:
                logger.warning("No movies added in the past week - check TMDB connection")
                
        except Exception as e:
            logger.error(f"Error during health check: {e}")
        finally:
            db.close()

# Initialize maintenance class
maintenance = MovieMaintenance()

# Schedule tasks
def schedule_tasks():
    """Schedule all maintenance tasks"""
    
    # Weekly tasks - run every Sunday at 2 AM
    schedule.every().sunday.at("02:00").do(maintenance.weekly_movie_update)
    schedule.every().sunday.at("03:00").do(maintenance.weekly_new_movies)
    
    # Monthly tasks - run on the 1st of each month at 4 AM
    schedule.every().month.at("04:00").do(maintenance.monthly_popular_movies)
    
    # Cleanup - run monthly on the 15th at 1 AM
    schedule.every().month.at("01:00").do(maintenance.cleanup_old_data)
    
    # Health check - run daily at midnight
    schedule.every().day.at("00:00").do(maintenance.health_check)
    
    logger.info("Maintenance tasks scheduled:")
    logger.info("  - Weekly movie updates: Every Sunday at 2:00 AM")
    logger.info("  - Weekly new movies: Every Sunday at 3:00 AM")
    logger.info("  - Monthly popular movies: 1st of each month at 4:00 AM")
    logger.info("  - Database cleanup: 15th of each month at 1:00 AM")
    logger.info("  - Health check: Daily at midnight")

def run_scheduler():
    """Run the scheduler in a loop"""
    logger.info("Starting maintenance scheduler...")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in scheduler: {e}")
            time.sleep(300)  # Wait 5 minutes before retrying

def run_scheduler_in_background():
    """Run scheduler in a background thread"""
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Maintenance scheduler started in background thread")
    return scheduler_thread

# Manual task execution functions (for testing)
def run_update_now():
    """Manually run movie update task"""
    logger.info("Manually running movie update task...")
    maintenance.weekly_movie_update()

def run_fetch_new_now():
    """Manually run new movies fetch task"""
    logger.info("Manually running new movies fetch task...")
    maintenance.weekly_new_movies()

def run_health_check_now():
    """Manually run health check"""
    logger.info("Manually running health check...")
    maintenance.health_check()

def run_cleanup_now():
    """Manually run cleanup task"""
    logger.info("Manually running cleanup task...")
    maintenance.cleanup_old_data()

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Movie Database Maintenance")
    parser.add_argument("--mode", choices=["schedule", "update", "fetch", "health", "cleanup"], 
                       default="schedule", help="Mode to run")
    
    args = parser.parse_args()
    
    # Initialize database
    await initialize_database()
    
    if args.mode == "schedule":
        # Schedule tasks and run continuously
        schedule_tasks()
        run_scheduler()
    elif args.mode == "update":
        run_update_now()
    elif args.mode == "fetch":
        run_fetch_new_now()
    elif args.mode == "health":
        run_health_check_now()
    elif args.mode == "cleanup":
        run_cleanup_now()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
