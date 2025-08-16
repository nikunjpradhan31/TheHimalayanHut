from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, File, UploadFile
from sqlalchemy.orm import Session
# from backend.models import *
# from backend.pydantic_models import *
# from backend.database import get_db
from models import *
from pydantic_models import *
from database import  get_db
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from collections import defaultdict
#from backend.tests.minio_function import upload_single_file
import io
from typing import Dict
import time
from pydantic import EmailStr
from .email import *
import re

router = APIRouter(prefix="/users", tags=["users"])

login_attempts: Dict[str, Dict] = {}

LOCKOUT_THRESHOLD = 3
LOCKOUT_TIME_SECONDS = 60 * 360

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
SECRET_KEY = "djfslerhi3n8r1y2329cn97shiwoj9wuxgfr3ni2uom"
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def _handle_failed_attempt(username: str):
    now = time.time()
    attempt_info = login_attempts.get(username)

    if attempt_info:
        if now - attempt_info["first_failed"] > LOCKOUT_TIME_SECONDS:
            login_attempts[username] = {"count": 1, "first_failed": now, "locked_until": None}
        else:
            attempt_info["count"] += 1
            if attempt_info["count"] >= LOCKOUT_THRESHOLD:
                attempt_info["locked_until"] = now + LOCKOUT_TIME_SECONDS
    else:
        login_attempts[username] = {"count": 1, "first_failed": now, "locked_until": None}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password",
    )

@router.post("/register", response_model=PreVerifyResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Session = Depends(get_db) ):

    if len(user.username)< 5:
        raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is too short"
            )
    if len(user.password) < 7:
        raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is too short"
            )
    db_user = db.query(Users).filter(Users.username == user.username).first()
    if db_user:
        if db_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        else:
            db.delete(db_user)
            db.commit()
    db_email = db.query(Users).filter(Users.email == user.email).first()

    if db_email:
        if db_email.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            db.delete(db_email)
            db.commit()

    if not is_valid_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not valid"
        )
    if user.password != user.confirmpassword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )


    hashed_password = hash_password(user.password)
    db_user = Users(
        username=user.username,
        email=user.email,
        password=hashed_password,
        joindate=datetime.now(), 
               
    )
    # expiration_time = datetime.now() + timedelta(hours=12)
    # expiration_timestamp = int(expiration_time.timestamp())

    # token_data = {"sub": user.username, "exp": expiration_timestamp}
    # token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")

    # db_user.session_at = datetime.now()
    # db_user.access_key = token

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    sent = await send_email_verification(email =  db_user.email, user_id = db_user.user_id, type_ver = "email_verify", db=db)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verfication was unable to be sent"
        )
    # user_res = LoginResponse(
    #     user_id = db_user.user_id,
    #     username=db_user.username,
    #     email=db_user.email,
    #     joindate=db_user.joindate,
    #     access_token=token,
    #     token_type="bearer",
    #     profile_picture=user.profile_picture,
    #     description = user.description,
    # )
    user_res = PreVerifyResponse(
        user_id = db_user.user_id,
        email = db_user.email,
        id = sent
    )

    return user_res

@router.post("/login", response_model=PreVerifyResponse)
async def login(user_login: UserLogin, db: Session = Depends(get_db)):
    now = time.time()

    attempt_info = login_attempts.get(user_login.username)
    if attempt_info:
        if attempt_info.get("locked_until") and now < attempt_info["locked_until"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Too many failed attempts. Try again in a minute."
            )

    if len(user_login.username) < 3 or len(user_login.password) < 7:
        return _handle_failed_attempt(user_login.username)

    user = db.query(Users).filter(Users.username == user_login.username).first()
    if not user or not verify_password(user_login.password, user.password):
        return _handle_failed_attempt(user_login.username)

    if user_login.username in login_attempts:
        del login_attempts[user_login.username]

    # expiration_time = datetime.now() + timedelta(hours=12)
    # expiration_timestamp = int(expiration_time.timestamp())

    # token_data = {"sub": user.username, "exp": expiration_timestamp}
    # token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")

    # user.session_at = datetime.now()
    # user.access_key = token
    #db.commit()
    sent = await send_email_verification(email = user.email, user_id=user.user_id, type_ver = "login", db=db)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verfication was unable to be sent"
        )
    # return LoginResponse(
    #     user_id=user.user_id,
    #     username=user.username,
    #     email=user.email,
    #     joindate=user.joindate,
    #     access_token=token,
    #     token_type="bearer",
    #     profile_picture=user.profile_picture,
    #     description=user.description,
    # )
    return PreVerifyResponse(
        user_id = user.user_id,
        email = user.email,
         id = sent
    )

@router.post("/verify", response_model=LoginResponse)
def verify_login(input: VerifyBase, db: Session = Depends(get_db)):
    record = (
        db.query(Verification)
        .filter(Verification.user_id==input.user_id, Verification.email==input.email, Verification.code==str(input.code), Verification.is_used==False, Verification.id == input.id)
        .first()
    )
    
    if not record:
        raise HTTPException(status_code=400, detail="Invalid verification code or user information.")
    
    if datetime.now() > record.expires_at:
        raise HTTPException(status_code=400, detail="Verification code has expired.")
    
    record.is_used = True

    user = db.query(Users).filter_by(user_id=input.user_id, email=input.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    expiration_time = datetime.now() + timedelta(hours=12)
    expiration_timestamp = int(expiration_time.timestamp())
    token_data = {"sub": user.username, "exp": expiration_timestamp}
    token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")
    user.session_at = datetime.now()
    user.access_key = token
    user.is_verified = True
    db.commit()

    return LoginResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        joindate=user.joindate,
        access_token=token,
        token_type="bearer",
        profile_picture=user.profile_picture,
        description=user.description,
    )

@router.get("/search/{substring}/{username}", status_code=status.HTTP_200_OK)
def get_user_of_substring(substring: str, username: str, db: Session = Depends(get_db)):
    # Get the user_id of the requester
    current_user = db.query(Users).filter(Users.username == username).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requesting user not found"
        )

    # Get IDs of all current friends
    friend_ids_subquery = db.query(Friends.user_one).filter(Friends.user_two == current_user.user_id)
    friend_ids_subquery = friend_ids_subquery.union(
        db.query(Friends.user_two).filter(Friends.user_one == current_user.user_id)
    ).subquery()

    # Query users whose username matches and are NOT current user or a friend
    users = db.query(Users).filter(
        Users.username.ilike(f"%{substring}%"),
        Users.username != username,
        ~Users.user_id.in_(friend_ids_subquery)
    ).limit(15).all()

    if not users:
        return []

    users_list = [
        UserResponse(
            username=user.username,
            user_id=user.user_id,
            email=user.email,
            joindate=user.joindate
        )
        for user in users
    ]
    return users_list

@router.post("/friends/request", status_code=status.HTTP_201_CREATED)
def create_friend_request(input: FriendRequestCreate,db:Session = Depends(get_db) ):
    user_one_exists = db.query(Users).filter(Users.user_id == input.user_one).first()
    user_two_exists = db.query(Users).filter(Users.user_id == input.user_two).first()

    if not user_one_exists or not user_two_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The account you are trying to add does not exist"
        )
    
    if user_one_exists.access_key != input.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )
    existing_request = db.query(Friends).filter(
        ((Friends.user_one == input.user_one) & (Friends.user_two == input.user_two)) |
        ((Friends.user_one == input.user_two) & (Friends.user_two == input.user_one))).first()
    
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already friends with this person"
        )
    request = Friends(
        user_one = input.user_one,
        user_two = input.user_two,
        created_at = datetime.now()
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    return request

@router.post("/friends/accept_request", status_code=status.HTTP_202_ACCEPTED)
def accept_friend_request(input: FriendRequestCreate ,db:Session = Depends(get_db)):
    user_one_exists = db.query(Users).filter(Users.user_id == input.user_one).first()
    user_two_exists = db.query(Users).filter(Users.user_id == input.user_two).first()

    if not user_one_exists or not user_two_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The account you are trying to add does not exist"
        )
    
    if user_two_exists.access_key != input.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )
    existing_request = db.query(Friends).filter(
        ((Friends.user_one == input.user_one) & (Friends.user_two == input.user_two)) |
        ((Friends.user_one == input.user_two) & (Friends.user_two == input.user_one))).first()
    existing_request.requested_user_accepted = True

    db.commit()
    db.refresh(existing_request)

    return existing_request

@router.get("/friends/get_all/{user_id}/{access_token}", response_model=AllFriendsResponse, status_code=status.HTTP_200_OK)
def get_all_friends(user_id: int,access_token:str, db: Session = Depends(get_db)):
    user_exists = db.query(Users).filter(Users.user_id == user_id).first()
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user does not exist"
        )
    if user_exists.access_key != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )

    friends = db.query(Friends).filter(
    ((Friends.user_one == user_id) | (Friends.user_two == user_id)) & (Friends.requested_user_accepted == True)
).all()


    if not friends:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail="You have no current friends"
        )
    friend_usernames = [
        friend.user_two if friend.user_one == user_id else friend.user_one
        for friend in friends
    ]

    friend_details = db.query(Users).filter(Users.user_id.in_(friend_usernames)).all()
    friends_response = [
        UserResponse(
            username = friend.username,
            user_id=friend.user_id,
            email=friend.email,
            joindate=friend.joindate
        )
        for friend in friend_details
    ]

    return AllFriendsResponse(friends=friends_response)

@router.get("/friends/get_all_requests/{user_id}/{access_token}", response_model=AllFriendsResponse, status_code=status.HTTP_200_OK)
def get_all_friends(user_id: int,access_token:str, db: Session = Depends(get_db)):
    user_exists = db.query(Users).filter(Users.user_id == user_id).first()
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user does not exist"
        )
    if user_exists.access_key != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )

    friends = db.query(Friends).filter(
    ((Friends.user_two == user_id)) & (Friends.requested_user_accepted == False)
).all()


    if not friends:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail="You have no current requests"
        )
    friend_usernames = [
        friend.user_one
        for friend in friends
    ]

    friend_details = db.query(Users).filter(Users.user_id.in_(friend_usernames)).all()
    friends_response = [
        UserResponse(
            username = friend.username,
            user_id=friend.user_id,
            email=friend.email,
            joindate=friend.joindate
        )
        for friend in friend_details
    ]

    return AllFriendsResponse(friends=friends_response)


@router.delete("/friends/remove/{user_id}/{friend_user_id}/{access_token}", status_code=status.HTTP_204_NO_CONTENT)
def remove_friend(user_id: int, friend_user_id: int,access_token: str, db: Session = Depends(get_db)):
    user_one_exists = db.query(Users).filter(Users.user_id == user_id).first()
    user_two_exists = db.query(Users).filter(Users.user_id == friend_user_id).first()

    if not user_one_exists or not user_two_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or both of the users do not exist"
        )
    if user_one_exists.access_key != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )
    friendship = db.query(Friends).filter(
        ((Friends.user_one == user_id) & (Friends.user_two == friend_user_id)) |
        ((Friends.user_one == friend_user_id) & (Friends.user_two == user_id))
    ).first()

    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend does not exist"
        )
    db.delete(friendship)
    db.query(Recommendation).filter(
        ((Recommendation.recommender == user_id) and (Recommendation.recommended == friend_user_id)) |
        ((Recommendation.recommender == friend_user_id) and (Recommendation.recommended == user_id))
    ).delete()
    db.commit()

@router.get("/recommendation/get/{user_id}/{access_token}", response_model=list[GroupedRecommendationResponse], status_code=status.HTTP_200_OK)
def get_recommendations_for_user(user_id: int,access_token:str, db: Session = Depends(get_db)):

    user = db.query(Users).filter(Users.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if user.access_key != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )

    recommendations = (
        db.query(Recommendation, Movie)
        .join(Movie, Recommendation.movie_id == Movie.movie_id)
        .filter(Recommendation.recommended == user_id)
        .all()
    )

    if not recommendations:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail="No recommendations found for this user"
        )
    
    grouped_recommendations = defaultdict(list)
    for rec, movie in recommendations:
        grouped_recommendations[rec.recommender].append({
            "movie_id": movie.movie_id,
            "title": movie.title,
            "image_url": movie.image_url,

        })
        result = [
        {"recommender": recommender, "movies": movies}
        for recommender, movies in grouped_recommendations.items()
    ]
    return result

@router.post("/recommendation/create", response_model=RecommendationResponse, status_code=status.HTTP_201_CREATED)
def create_recommendation(
    input: RecommendationCreate,
    db: Session = Depends(get_db),
):
    recommender_exists = db.query(Users).filter(Users.user_id == input.recommender).first()
    if not recommender_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recommender does not exist"
        )
    if recommender_exists.access_key != input.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )
    recommended_exists = db.query(Users).filter(Users.user_id == input.recommended).first()
    if not recommended_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recommended user does not exist"
        )

    movie_exists = db.query(Movie).filter(Movie.movie_id == input.movie_id).first()
    if not movie_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie does not exist"
        )

    existing_recommendation = db.query(Recommendation).filter(
        (Recommendation.recommender == input.recommender) &
        (Recommendation.recommended == input.recommended) &
        (Recommendation.movie_id == input.movie_id)
    ).first()

    if existing_recommendation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already recommended this movie to this user"
        )

    new_recommendation = Recommendation(
        recommender=input.recommender,
        recommended=input.recommended,
        movie_id=input.movie_id,
    )
    db.add(new_recommendation)
    db.commit()
    db.refresh(new_recommendation)

    return RecommendationResponse(
        recommender=new_recommendation.recommender,
        recommended=new_recommendation.recommended,
        movie_id=new_recommendation.movie_id,
    )

@router.post("/recommendation/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_recommendation(
    input: RecommendationDelete,
    db: Session = Depends(get_db),
):
    # Authenticate requesting user
    user = db.query(Users).filter(Users.user_id == input.requesting_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requesting user does not exist"
        )

    if user.access_key != input.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You are unauthorized"
        )

    # Determine correct recommender/recommended based on flag
    recommender_id = input.requesting_user_id if input.is_recommender else input.other_user_id
    recommended_id = input.other_user_id if input.is_recommender else input.requesting_user_id

    # Query the exact recommendation
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommender == recommender_id,
        Recommendation.recommended == recommended_id,
        Recommendation.movie_id == input.movie_id
    ).first()

    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )

    db.delete(recommendation)
    db.commit()
    return 


# @router.post("/update_profile")
# async def update_user(
#     user_id: int = Form(...),
#     username: str = Form(None),
#     access_key: str = Form(...),
#     description: Optional[str] = Form(None),
#     file: Optional[UploadFile] = File(None),
#     db: Session = Depends(get_db)
# ):
#     user = db.query(Users).filter(Users.user_id == user_id).first()
#     if not user or user.access_key != access_key:
#         raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="This is user does not exist or was not valid"
#             )
#     if username:
#         does_username_exist = db.query(Users).filter(Users.username == username).first()
#         if does_username_exist:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="This username is taken"
#             )
#         user.username = username
#     db.commit()
#     db.refresh(user)
#     if description:
#         user.description = description
#     db.commit()
#     db.refresh(user)
#     if file:
#         file_key = f"profile_pictures/{user_id}_{user.username}"
#         bucket_name = "production" 
#         file_content = await file.read()
#         file_stream = io.BytesIO(file_content)
#         # try:
#         upload_single_file(bucket=bucket_name,object_name=file_key,data=file_stream,content_type=file.content_type)
#         user.profile_picture = file_key
#         db.commit()
#         db.refresh(user)
#         # finally:
#         #     raise HTTPException(
#         #         status_code=status.HTTP_400_BAD_REQUEST,
#         #         detail="Unable to upload profile picture"
#         #     )
#     return

# @router.post("/update_profile")
# async def update_user(
#     input: UserUpdate,
#     db: Session = Depends(get_db)
# ):
#     user = db.query(Users).filter(Users.user_id == input.user_id).first()
#     if not user or user.access_key != input.access_key:
#         raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="This is user does not exist or was not valid"
#             )
#     if input.username:
#         does_username_exist = db.query(Users).filter(Users.username == input.username).first()
#         if does_username_exist:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="This username is taken"
#             )
#         user.username = input.username
#     db.commit()
#     db.refresh(user)
#     if input.description:
#         user.description = input.description
#     db.commit()
#     db.refresh(user)
#     if input.isfile:
#         file_key = f"profile_pictures/{user.user_id}_{user.username}"
#         bucket_name = "production" 
#         presigned_url = create_presigned_put_url(bucket_name, file_key)
#         if presigned_url:
#             return {"presigned_url": presigned_url, "file_key": file_key}
#         else:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Unable to upload file"
#             )
#     return
