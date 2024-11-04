import logging
from struct import pack
import re
import base64
from pyrogram.file_id import FileId
from database.users_chats_db import get_database_connection
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from info import DATABASE_URL, DATABASE_NAME, COLLECTION_NAME, MAX_BTN

client = AsyncIOMotorClient(DATABASE_URL)
db = client[DATABASE_NAME]
instance = Instance.from_db(db)

@instance.register
class Media(Document):
    file_id = fields.StrField(attribute='_id')
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    caption = fields.StrField(allow_none=True)

    class Meta:
        indexes = ('$file_name', )
        collection_name = COLLECTION_NAME

async def save_file(media):
    """Save file in database"""

    # TODO: Find better way to get same file_id for same media to avoid duplicates
    file_id = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name))
    file_caption = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.caption))
    try:
        file = Media(
            file_id=file_id,
            file_name=file_name,
            file_size=media.file_size,
            caption=file_caption
        )
    except ValidationError:
        print(f'Saving Error - {file_name}')
        return 'err'
    else:
        try:
            await file.commit()
        except DuplicateKeyError:      
            print(f'Already Saved - {file_name}')
            return 'dup'
        else:
            print(f'Saved - {file_name}')
            return 'suc'

async def get_search_results(query, max_results=MAX_BTN, offset=0, lang=None):
    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]') 
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        regex = query

    filter = {'file_name': regex}
    cursor = Media.find(filter)

    # Sort by recent
    cursor.sort('$natural', -1)

    if lang:
        lang_files = [file async for file in cursor if lang in file.file_name.lower()]
        files = lang_files[offset:][:max_results]
        total_results = len(lang_files)
        next_offset = offset + max_results
        if next_offset >= total_results:
            next_offset = ''
        return files, next_offset, total_results
        
    # Slice files according to offset and max results
    cursor.skip(offset).limit(max_results)
    # Get list of files
    files = await cursor.to_list(length=max_results)
    total_results = await Media.count_documents(filter)
    next_offset = offset + max_results
    if next_offset >= total_results:
        next_offset = ''       
    return files, next_offset, total_results

async def delete_files(query):
    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        regex = query
    filter = {'file_name': regex}
    total = await Media.count_documents(filter)
    files = Media.find(filter)
    return total, files

async def get_file_details(query):
    filter = {'file_id': query}
    cursor = Media.find(filter)
    filedetails = await cursor.to_list(length=1)
    return filedetails

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0

            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    return file_id


class IAF:
    def __init__(self):
        # MongoDB client aur collections initialize
        self.client = AsyncIOMotorClient(DATABASE_URL)
        self.db = self.client[DATABASE_NAME]
        self.movies_col = self.db['movies']
        self.requests_col = self.db['movie_requests']
   

    async def add_movie_request(self, movie_name, language, user_id):
        await self.requests_col.insert_one({
            'movie_name': movie_name,
            'language': language,
            'user_id': user_id
        })

    async def search_movie_by_name(self, movie_name):
        movies = await self.movies_col.find({'movie_name': movie_name}).to_list(length=None)
        return [movie['language'] for movie in movies] if movies else []

    async def check_and_notify_request(self, movie_name, language, bot):
        requesters = await self.requests_col.find({'movie_name': movie_name, 'language': language}).to_list(length=None)
        user_ids = [req['user_id'] for req in requesters]
        
        for user_id in user_ids:
            await bot.send_message(
                chat_id=user_id,
                text=f"'{movie_name}' ({language}) ab available hai!"
            )
        
        await self.requests_col.delete_many({'movie_name': movie_name, 'language': language})

    async def check_movie_in_database(self, movie_name, language=None):
        query = {'movie_name': movie_name}
        if language:
            query['language'] = language
        
        movie = await self.movies_col.find_one(query)
        return movie is not None  # Movie milne par True return karega
