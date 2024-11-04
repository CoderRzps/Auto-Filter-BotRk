import logging
import re
import base64
from struct import pack
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from database.users_chats_db import get_database_connection
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from info import DATABASE_URL, DATABASE_NAME, COLLECTION_NAME, MAX_BTN

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection setup
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
        indexes = ('$file_name',)
        collection_name = COLLECTION_NAME

async def check_movie_in_database(movie_name: str) -> bool:
    """
    Check if a movie exists in the database.
    
    Args:
        movie_name (str): The name of the movie to check.

    Returns:
        bool: True if the movie exists in the database, otherwise False.
    """
    db = await get_database_connection()
    try:
        query = {"name": movie_name}
        count = await db.movies.count_documents(query)
        return count > 0  # Return True if movie exists
    except Exception as e:
        logger.error(f"Error checking movie in database: {e}")
        return False
        
async def save_file(media):
    """Save a file in the database."""

    file_id = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name))
    file_caption = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.caption))
    
    # HD version check to delete old dubbed files
    if "hd" in file_name.lower():
        old_filter = {
            "file_name": re.compile(re.escape(file_name), re.IGNORECASE),
            "file_name": {"$regex": "dubbed", "$options": "i"}
        }
        old_files = Media.find(old_filter)

        async for old_file in old_files:
            try:
                await Media.delete_one({"_id": old_file.file_id})
                logger.info(f"Deleted old dubbed version - {old_file.file_name}")
            except Exception as e:
                logger.error(f"Error deleting old dubbed file - {old_file.file_name}: {e}")

    # New HD file save
    try:
        file = Media(
            file_id=file_id,
            file_name=file_name,
            file_size=media.file_size,
            caption=file_caption
        )
        await file.commit()
        logger.info(f'Saved - {file_name}')
        return 'suc'
    except ValidationError as ve:
        logger.error(f"Validation error while saving - {file_name}: {ve}")
        return 'err'
    except DuplicateKeyError:
        logger.info(f'Already Saved - {file_name}')
        return 'dup'
    except Exception as e:
        logger.error(f"Error while saving file - {file_name}: {e}")
        return 'err'

async def get_search_results(query, max_results=MAX_BTN, offset=0, lang=None):
    """
    Get search results from the database.

    Args:
        query (str): The search query.
        max_results (int): The maximum number of results to return.
        offset (int): The offset for pagination.
        lang (str): The language filter.

    Returns:
        tuple: A tuple containing the list of files, next offset, and total results.
    """
    query = query.strip()
    raw_pattern = re.escape(query) if query else '.'
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except Exception as e:
        logger.error(f"Regex compilation error: {e}")
        regex = query

    filter = {'file_name': regex}
    cursor = Media.find(filter).sort('$natural', -1)

    if lang:
        lang_files = [file async for file in cursor if lang in file.file_name.lower()]
        total_results = len(lang_files)
        files = lang_files[offset:][:max_results]
        next_offset = offset + max_results if next_offset < total_results else ''
        return files, next_offset, total_results
        
    # Slice files according to offset and max results
    cursor = cursor.skip(offset).limit(max_results)
    files = await cursor.to_list(length=max_results)
    total_results = await Media.count_documents(filter)
    next_offset = offset + max_results if next_offset < total_results else ''       
    return files, next_offset, total_results

async def delete_files(query):
    """
    Delete files matching the query.

    Args:
        query (str): The query to match files.

    Returns:
        tuple: Total number of matching files and an async cursor.
    """
    query = query.strip()
    raw_pattern = re.escape(query) if query else '.'

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except Exception as e:
        logger.error(f"Regex compilation error: {e}")
        regex = query
    filter = {'file_name': regex}
    total = await Media.count_documents(filter)
    files = Media.find(filter)
    return total, files

async def get_file_details(query):
    """
    Get details of a file by its file_id.

    Args:
        query (str): The file_id of the file.

    Returns:
        list: List of file details.
    """
    filter = {'file_id': query}
    cursor = Media.find(filter)
    filedetails = await cursor.to_list(length=1)
    return filedetails

def encode_file_id(s: bytes) -> str:
    """Encode the file ID."""
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
    """Unpack a new file ID."""
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
