from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, case

from models import *
from pydantic_models import *
from database import get_db, initialize_database
import asyncio
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import coo_matrix
from sklearn.preprocessing import LabelEncoder
import pandas as pd
from sqlalchemy.sql import text
from implicit.als import AlternatingLeastSquares


def get_movie_data(db: Session = Depends(get_db)):
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

    return pd.DataFrame(movies_data)

def movie_based_recommendation(movie_id, db,top_n=5):
    df = get_movie_data(db)
    tfidf = TfidfVectorizer(stop_words='english')
    
    df['content'] = df['description'] + ' ' + df['genres'] + ' ' + df['director'] + ' ' + df['actors']
    df['content'] = df['content'].fillna('')

    tfidf_matrix = tfidf.fit_transform(df['content'])
    
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
    
    idx = df[df['movie_id'] == movie_id].index[0]
    
    sim_scores = list(enumerate(cosine_sim[idx]))
    
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    
    sim_scores = [score for score in sim_scores if df['movie_id'].iloc[score[0]] != movie_id]

    top_movies = sim_scores[1:top_n+1]
    top_movie_indices = [i[0] for i in top_movies]
    
    recommended_movies = df['title'].iloc[top_movie_indices]
    return recommended_movies.tolist()

def user_collaborative_recommendation(user_id,db,top_n=20):
    df = get_movie_data(db)
    query = text("""SELECT 
                        u.user_id as User, 
                        m.movie_id as Movie,
                        CASE 
                            WHEN utm.has_watched = TRUE THEN 1
                            ELSE 0
                        END AS Check
                    FROM 
                        users AS u
                    CROSS JOIN 
                        movie AS m
                    LEFT OUTER JOIN 
                        usertomovie AS utm 
                        ON u.user_id = utm.user_id AND m.movie_id = utm.movie_id;
                """)

    results = db.execute(query).fetchall()
    user_ids = []
    movie_ids = []
    data = []

    for user, movie, check in results:
        if check == 1: 
            user_ids.append(user)
            movie_ids.append(movie)
            data.append(1)
    user_encoder = LabelEncoder()
    movie_encoder = LabelEncoder()

    user_indexes = user_encoder.fit_transform(user_ids)
    movie_indexes = movie_encoder.fit_transform(movie_ids)
    num_users = len(user_encoder.classes_)
    num_movies = len(movie_encoder.classes_)
    matrix = coo_matrix((data, (user_indexes, movie_indexes)), shape=(num_users,num_movies))
    CSR_Matrix = matrix.tocsr()

    model = AlternatingLeastSquares(factors=64, regularization=0.1, iterations=15,use_gpu=False)
    alpha = 80
    weighted = (CSR_Matrix * alpha).astype("double")
    model.fit(weighted)

    user_internal_id = user_encoder.transform([user_id])[0]
    recommended_movies = model.recommend(userid=user_internal_id, user_items=weighted[user_internal_id], N=top_n)
    movie_ids, _ = recommended_movies
    decode = lambda mid: movie_encoder.inverse_transform([mid])[0]
    filtered_movie_ids = [decode(mid) for mid in (movie_ids)]
    movies = df[df['movie_id'].isin(filtered_movie_ids) ]
    return

def get_user_watched_movies(user_id,db):
    movies = db.query(UserToMovie.movie_id).filter(UserToMovie.user_id == user_id,UserToMovie.has_watched == True).all()
    movie_ids_list = [movie_id for (movie_id,) in movies]
    return movie_ids_list

def get_watchlist_movies(watchlist_id,db):
    movies = db.query(MoviesInWatchList.movie_id).filter(MoviesInWatchList.watchlist_id == watchlist_id).all()
    movie_ids_list = [movie_id for (movie_id,) in movies]
    return movie_ids_list

def user_content_recommendations(ID,db, type_rec=1, top_n=20):
    all_movies = get_movie_data(db)
    if type_rec == 1:
        selected_movies = get_user_watched_movies(ID,db)
    else:
        selected_movies = get_watchlist_movies(ID,db)
    if not selected_movies:
        return
    all_movies['content'] = (all_movies['description'] + ' ' + all_movies['genres'] + ' ' +
                     all_movies['director'] + ' ' + all_movies['actors']).fillna('')
    TFIDF = TfidfVectorizer(stop_words='english')
    matrix = TFIDF.fit_transform(all_movies['content'])

    selected_indices = all_movies[all_movies['movie_id'].isin(selected_movies)].index

    user_sim_vector = cosine_similarity(matrix[selected_indices], matrix)
    mean_scores = user_sim_vector.mean(axis=0)

    mean_scores[selected_indices] = -1

    top_indices = mean_scores.argsort()[-top_n:][::-1]

    recommended_movies = all_movies.iloc[top_indices]['title'].tolist()
    return recommended_movies

async def main():
    await initialize_database()
    
    db = next(get_db()) 
    
    try:
        #user_collaborative_recommendation(2,db,5)
        #movie_based_recommendation(5,db,5)
        user_content_recommendations(1,db,1,20)
        #user_content_recommendations(1,db,0,20)
    finally:
        db.close()



if __name__ == "__main__":
    asyncio.run(main())



