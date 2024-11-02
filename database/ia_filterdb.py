import logging
import re
import base64
from struct import pack
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from info import DATABASE_URL, DATABASE_NAME, COLLECTION_NAME, MAX_BTN

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Client Setup
client = AsyncIOMotorClient(DATABASE_URL)
db = client[DATABASE_NAME]
instance = Instance.from_db(db)

@instance.register
class Media(Document):
    file_id = fields.StrField(attribute='_id')  # Using file_id as unique identifier
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    caption = fields.StrField(allow_none=True)

    class Meta:
        indexes = ('$file_name', )
        collection_name = COLLECTION_NAME

# Save file to database
async def save_file(media):
    """Save file in database with duplicate handling and error logging"""

    file_id = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name))
    file_caption = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.caption))

    # Check and delete old dubbed files if "HD" is present in the name
    if "hd" in file_name.lower():
        old_filter = {
            "file_name": {"$regex": "holl dubbed", "$options": "i"}
        }
        old_files = Media.find(old_filter)
        
        async for old_file in old_files:
            await Media.delete_one({"_id": old_file.file_id})
            logger.info(f"Deleted old dubbed version - {old_file.file_name}")

    # Try to save new HD file
    try:
        file = Media(
            file_id=file_id,
            file_name=file_name,
            file_size=media.file_size,
            caption=file_caption
        )
        await file.commit()
    except ValidationError:
        logger.error(f'Saving Error - {file_name}')
        return 'err'
    except DuplicateKeyError:      
        logger.info(f'Already Saved - {file_name}')
        return 'dup'
    else:
        logger.info(f'Saved - {file_name}')
        return 'suc'

# Search files in database
async def get_search_results(query, max_results=MAX_BTN, offset=0, lang=None):
    query = query.strip()
    raw_pattern = '.'
    if query:
        if ' ' not in query:
            raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
        else:
            raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]') 

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except re.error:
        regex = query

    filter = {'file_name': regex}
    cursor = Media.find(filter)
    cursor.sort('$natural', -1)  # Sort by recent

    if lang:
        lang_files = [file async for file in cursor if lang in file.file_name.lower()]
        files = lang_files[offset:][:max_results]
        total_results = len(lang_files)
        next_offset = offset + max_results
        return files, (next_offset if next_offset < total_results else ''), total_results

    cursor.skip(offset).limit(max_results)
    files = await cursor.to_list(length=max_results)
    total_results = await Media.count_documents(filter)
    next_offset = offset + max_results
    return files, (next_offset if next_offset < total_results else ''), total_results

# Delete files based on query
async def delete_files(query):
    query = query.strip()
    raw_pattern = '.'
    if query:
        if ' ' not in query:
            raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
        else:
            raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except re.error:
        regex = query
    filter = {'file_name': regex}
    total = await Media.count_documents(filter)
    files = Media.find(filter)
    return total, files

# Get file details by ID
async def get_file_details(query):
    filter = {'file_id': query}
    cursor = Media.find(filter)
    return await cursor.to_list(length=1)

# Encode file ID
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

# Unpack file ID
def unpack_new_file_id(new_file_id):
    decoded = FileId.decode(new_file_id)
    return encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
