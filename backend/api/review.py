# from fastapi import APIRouter, Depends, HTTPException, status, Query
# from sqlalchemy.orm import Session
# # from backend.models import *
# # from backend.pydantic_models import *
# # from backend.database import get_db
# from models import *
# from pydantic_models import *
# from database import SyncSessionLocal, get_db
# from passlib.context import CryptContext
# import jwt
# from datetime import datetime, timedelta
# from collections import defaultdict


# router = APIRouter(prefix="/review", tags=["review"])

# @router.post("/create",response_model=ReviewResponseUser, status_code=status.HTTP_201_CREATED)
# def create_review(input: ReviewCreate,  db: Session = Depends(get_db)):
#     user = db.query(Users).filter(Users.user_id == input.user_id).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="User does not exist",
#         )
#     if user.access_key != input.access_token:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="You are unauthorized"
#         )
#     movie = db.query(Movie).filter(Movie.movie_id == input.movie_id).first()
#     if not movie:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Movie does not exist",
#         )
    
#     review = db.query(Review).filter(Review.movie_id == input.movie_id, Review.user_id == input.user_id).first()
#     if review:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="You have already reviewed this movie"
#         )
#     OutputReview = Review(

#         user_id = input.user_id,
#         movie_id = input.movie_id,
#         rating = input.rating,
#         created_at= datetime.now(),
#         comment= input.comment,

#     )
#     db.add(OutputReview)
#     db.commit()
#     db.refresh(OutputReview)

#     return OutputReview

# @router.post("/update",response_model=ReviewResponseUser, status_code=status.HTTP_202_ACCEPTED)
# def update_review(input: ReviewCreate,  db: Session = Depends(get_db)):
#     user = db.query(Users).filter(Users.user_id == input.user_id).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="User does not exist",
#         )
#     if user.access_key != input.access_token:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="You are unauthorized"
#         )
#     movie = db.query(Movie).filter(Movie.movie_id == input.movie_id).first()
#     if not movie:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Movie does not exist",
#         )
    
#     review = db.query(Review).filter(Review.movie_id == input.movie_id, Review.user_id == input.user_id).first()
#     if not review:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="You have not reviewd this movie yet"
#         )

#     review.comment = input.comment
#     review.rating = input.rating

#     db.commit()
#     db.refresh(review)

#     return review

# @router.delete("/delete/{user_id}/{movie_id}/{access_token}", status_code=status.HTTP_204_NO_CONTENT)
# def delete_review(user_id: int,movie_id: int, access_token:str, db: Session = Depends(get_db)):
#     review = db.query(Review).filter(Review.user_id == user_id, Review.movie_id == movie_id).first()
#     if not review:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="You have not reviewd this movie"
#         )
#     user = db.query(Users).filter(Users.user_id == user_id).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="User does not exist",
#         )
#     if user.access_key != access_token:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="You are unauthorized"
#         )
    
#     db.delete(review)
#     db.commit()
#     return

# # @router.get("/movie/get_review/{movie_id}",response_model=ReviewsResponse, status_code=status.HTTP_200_OK)
# # def get_reviews_of_movie(movie_id: int, db: Session = Depends(get_db)):
# #     movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
# #     if not movie:
# #         raise HTTPException(
# #             status_code=status.HTTP_400_BAD_REQUEST,
# #             detail="This movie does not exist"
# #         )
# #     reviews = db.query(Review, Users.username).join(Users, Users.user_id == Review.user_id).filter(Review.movie_id == movie_id).all()
# #     if not reviews:
# #         raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="No reviews were found for this movie")
# #     review_list = [
# #         ReviewResponse(
# #             user_id=review.Review.user_id,
# #             movie_id=review.Review.movie_id,
# #             rating=review.Review.rating,
# #             comment=review.Review.comment,
# #             created_at=review.Review.created_at,
# #             username=review.username
# #         )
# #         for review in reviews
# #     ]
# #     return ReviewsResponse(reviews=review_list)

# @router.get(
#     "/movie/get_review/{movie_id}",
#     response_model=ReviewsResponse,
#     status_code=status.HTTP_200_OK
# )
# def get_reviews_of_movie(
#     movie_id: int,
#     page: int = Query(1, ge=1, description="Page number"),
#     page_size: int = Query(15, ge=1, le=100, description="Reviews per page"),
#     db: Session = Depends(get_db)
# ):
#     movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
#     if not movie:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="This movie does not exist"
#         )

#     offset = (page - 1) * page_size

#     reviews = (
#         db.query(Review, Users.username)
#         .join(Users, Users.user_id == Review.user_id)
#         .filter(Review.movie_id == movie_id)
#         .offset(offset)
#         .limit(page_size)
#         .all()
#     )

#     if not reviews:
#         raise HTTPException(
#             status_code=status.HTTP_204_NO_CONTENT,
#             detail="No reviews were found for this movie"
#         )

#     review_list = [
#         ReviewResponse(
#             user_id=review.Review.user_id,
#             movie_id=review.Review.movie_id,
#             rating=review.Review.rating,
#             comment=review.Review.comment,
#             created_at=review.Review.created_at,
#             username=review.username
#         )
#         for review in reviews
#     ]
#     return ReviewsResponse(reviews=review_list)

# @router.get("/users/get_review/{user_id}", status_code=status.HTTP_200_OK)
# def get_user_reviews(user_id: int, db: Session = Depends(get_db)):
#     user = db.query(Users).filter(Users.user_id == user_id).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="This user does not exist"
#         )
    
#     reviews = db.query(Review).filter(Review.user_id == user_id).all()
#     if not reviews:
#         raise HTTPException(status_code=404, detail="No reviews were found for this account")
#     return ReviewsResponseUser(reviews=reviews)
