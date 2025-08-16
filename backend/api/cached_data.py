import asyncio
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, File, UploadFile
from database import get_db
from models import *
import pandas as pd
import logging
logging.basicConfig(level=logging.INFO)

cached_movie_data = {"data": None}

def get_movie_data(db: Session):
    
    movies_query = db.query(Movie).all()
    genres_query = db.query(GenresToMovie).all()
    actors_query = db.query(ActorToMovie).all()
    directors_query = db.query(DirectorToMovie).all()

    genre_map = {}
    actor_map = {}
    director_map = {}

    for genre in genres_query:
        if genre.movie_id not in genre_map:
            genre_map[genre.movie_id] = []
        genre_map[genre.movie_id].append(genre.genre_name)
    for actor in actors_query:
        if actor.movie_id not in actor_map:
            actor_map[actor.movie_id] = []
        actor_map[actor.movie_id].append(actor.actor_name)
    for director in directors_query:
        director_map[director.movie_id] = director.director_name

    movies_data = []
    for movie in movies_query:
        genres_string = ', '.join(genre_map.get(movie.movie_id, []))
        actors_string = ', '.join(actor_map.get(movie.movie_id, []))
        director = director_map.get(movie.movie_id, None)

        movies_data.append({
            'movie_id': movie.movie_id,
            'title': movie.title,
            'description': movie.description,
            'genres': genres_string,
            'director': director,
            'actors': actors_string
        })

    movie_df = pd.DataFrame(movies_data)
    movie_df['content'] = (movie_df['description'] + ' ' + movie_df['genres'] + ' ' +
                     movie_df['director'] + ' ' + movie_df['actors']).fillna('')
    cached_movie_data['data'] =  movie_df
    logging.info("✅ Fetched Movie Data")



async def periodic_refresh(interval_minutes=30):
    while True:
        db_gen = get_db()
        db = next(db_gen)
        try:
            get_movie_data(db)
        finally:
            db_gen.close() 
        await asyncio.sleep(interval_minutes*60)

