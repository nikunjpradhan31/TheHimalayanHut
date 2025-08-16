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


# router = APIRouter(prefix="/event")

# @router.post("/create",response_model=EventResponse,status_code=status.HTTP_201_CREATED)
# def Create_Event(input: EventCreate,  db: Session = Depends(get_db)):
#     if(input.watchlist_id):
#         watchlist = db.query(WatchList).filter(WatchList.watchlist_id == input.watchlist_id).first()
#         if not watchlist:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="No WatchList was found"
#             )
#     user = db.query(Users).filter(Users.user_id == input.event_creator).first()
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
#     event = Event(
#         event_creator = input.event_creator,
#         event_time = input.event_time,
#         event_name = input.event_name,
#         event_location = input.event_location,
#         description = input.description,
#         watchlist_id = input.watchlist_id,
#         is_public = input.is_public,
#     )
#     db.add(event)
#     db.commit()
#     db.refresh(event)
#     user = db.query(Users).filter(Users.user_id == event.event_creator).first()
#     even = EventResponse(
#         event_id= event.event_id,
#         event_time= event.event_time,
#         event_name= event.event_name,
#         event_creator_name=user.username,
#         watchlist_id=event.watchlist_id,
#         description= event.description,
#         is_public= event.is_public,
#         event_location= event.event_location,
#         event_creator=event.event_creator

#     )
#     return even

# @router.delete("/delete/{event_id}/{access_token}",status_code=status.HTTP_204_NO_CONTENT)
# def Delete_Event(event_id: int,access_token:str, db: Session = Depends(get_db)):
#     event = db.query(Event).filter(Event.event_id == event_id).first()
#     if not event:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             details = "No event was found"
#         )
#     user = db.query(Users).filter(Users.user_id == event.event_creator).first()
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
#     #db.query(EventInvitees).filter(EventInvitees.event_id == event_id).delete()
#     db.delete(event)
#     db.commit()
#     return

# @router.put("/update/",response_model=EventResponse,status_code=status.HTTP_200_OK)
# def update_event(input:EventUpdateResponse,db:Session=Depends(get_db)):
#     event = db.query(Event).filter(Event.event_id == input.event_id).first()
    
#     if input.watchlist_id != None:
#         watchlist = db.query(WatchList).filter(WatchList.watchlist_id == input.watchlist_id).first()
#         if not watchlist:
#             raise HTTPException(status_code=404, detail="Watchlist not found")

#     if not event:
#         raise HTTPException(status_code=404, detail="Event not found")
#     user = db.query(Users).filter(Users.user_id == input.event_creator).first()
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
#     event.event_creator = input.event_creator
#     event.event_time = input.event_time
#     event.event_name = input.event_name
#     event.event_location = input.event_location
#     event.description = input.description
#     event.watchlist_id = input.watchlist_id
#     event.is_public = input.is_public

#     db.commit()
#     db.refresh(event)
#     user = db.query(Users).filter(Users.user_id == input.event_creator).first()

#     return EventResponse(
#         event_id= event.event_id,
#         event_time= event.event_time,
#         event_name= event.event_name,
#         event_creator_name=user.username,
#         watchlist_id=event.watchlist_id,
#         description= event.description,
#         is_public= event.is_public,
#         event_location= event.event_location,
#         event_creator=event.event_creator

#     )

# @router.get("/users/{user_id}/{access_token}",response_model=EventResponseList,status_code=status.HTTP_200_OK)
# def user_events(user_id:int,access_token: str, db:Session=Depends(get_db)):
#     events = db.query(Event).filter(Event.event_creator == user_id).all()
#     if not events:
#         raise HTTPException(status_code=204, detail="You do not have any events")
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
#     event_response = [
#         EventResponse(
#             event_id=event.event_id,
#             event_time=event.event_time,
#             event_name=event.event_name,
#             event_creator_name=user.username,  
#             watchlist_id=event.watchlist_id,
#             description=event.description,
#             is_public=event.is_public,
#             event_location=event.event_location,
#             event_creator=event.event_creator


#         ) for event in events
#     ]
#     return EventResponseList(events=event_response)

# @router.get("/invited/{user_id}/{access_token}",response_model=EventResponseList,status_code=status.HTTP_200_OK)
# def invited_events(user_id:int, access_token:str, db:Session=Depends(get_db)):
#     invitedevents = db.query(EventInvitees).filter(EventInvitees.invitee == user_id).all()
#     invidedevents_ids = [event.event_id for event in invitedevents]
#     events = db.query(Event).filter(Event.event_id.in_(invidedevents_ids)).all()
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
#     if not events:
#         raise HTTPException(status_code=204, detail="You do not have any invited events")
#     event_responses = []
#     for event in events:
#         user = db.query(Users).filter(Users.user_id == event.event_creator).first()
#         event_responses.append(
#             EventResponse(
#                 event_id=event.event_id,
#                 event_time=event.event_time,
#                 event_name=event.event_name,
#                 event_creator_name=user.username,
#                 watchlist_id=event.watchlist_id,
#                 description=event.description,
#                 is_public=event.is_public,
#                 event_location=event.event_location,
#                 event_creator=event.event_creator

#             )
#         )
#     return EventResponseList(events=event_responses)

# @router.get("/public/{user_id}/{substring}", response_model=EventResponseList, status_code=status.HTTP_200_OK)
# def public_events(
#     user_id: int, 
#     substring: str, 
#     db: Session = Depends(get_db)
# ):
#     if not substring.strip():
#         raise HTTPException(status_code=400, detail="Search substring cannot be empty")

#     events = (
#         db.query(Event)
#         .filter(
#             Event.is_public == True,
#             Event.event_creator != user_id,
#             Event.event_name.ilike(f"%{substring}%")
#         )
#         .limit(10)
#         .all()
#     )

#     if not events:
#         raise HTTPException(status_code=204, detail="No public events are found matching the criteria")
#     event_responses = []
#     for event in events:
#         user = db.query(Users).filter(Users.user_id == event.event_creator).first()
#         event_responses.append(
#             EventResponse(
#                 event_id=event.event_id,
#                 event_time=event.event_time,
#                 event_name=event.event_name,
#                 event_creator_name=user.username,
#                 watchlist_id=event.watchlist_id,
#                 description=event.description,
#                 is_public=event.is_public,
#                 event_location=event.event_location,
#                 event_creator=event.event_creator
#             )
#         )
#     return EventResponseList(events=event_responses)

# @router.post("/add_invitee",response_model = EventInviteesResponse, status_code=status.HTTP_201_CREATED)
# def add_invitee(input: EventInviteesCreate, db: Session=Depends(get_db)):
#     Ifinvitedalready = db.query(EventInvitees).filter(EventInvitees.event_id == input.event_id, EventInvitees.invitee == input.invitee).first()
#     if Ifinvitedalready:
#         raise HTTPException(status_code=400, detail="This person is already invited to the event")
#     event = db.query(Event).filter(Event.event_id == input.event_id).first()
#     user = db.query(Users).filter(Users.user_id == event.event_creator).first()
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
#     invite = EventInvitees(
#         event_id = input.event_id,
#         invitee = input.invitee
#     )
#     db.add(invite)
#     db.commit()
#     db.refresh(invite)
#     return invite

# @router.get("/invited_users/{event_id}", status_code=status.HTTP_200_OK)
# def invited_users_event(event_id:int,db:Session=Depends(get_db)):
#     event_peoples = db.query(EventInvitees).filter(EventInvitees.event_id == event_id).all()
#     if not event_peoples:
#         raise HTTPException(status_code=204, detail="No one has been invited to this event")
#     user_ids = [event.invitee for event in event_peoples]
#     people = db.query(Users).filter(Users.user_id.in_(user_ids)).all()

#     invited_users =[ 
#         OtherUserResponse (
#             user_id= user.user_id,
#             username=user.username,
#         ) for user in people]
#     return invited_users

