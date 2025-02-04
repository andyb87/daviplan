import logging
import json
import time
import channels.layers
try:
    # redis 4.*
    from redis.asyncio import RedisError
except ModuleNotFoundError:
    # redis 3.*
    from redis import RedisError
from redis.exceptions import ConnectionError as RedisConnectionError
from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer

import logging
logger = logging.getLogger(__name__)

channel_layer = channels.layers.get_channel_layer()

def send(channel: str, message: str, log_type: str='log_message',
         status={}, **kwargs):
    rec = {
        'message': message,
        'type': log_type,
        'timestamp': time.strftime('%d.%m.%Y %H:%M:%S'),
        'status': status,
    }
    rec.update(kwargs)

    async_to_sync(channel_layer.group_send)(channel, rec)


class WebSocketHandler(logging.StreamHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self.setFormatter(logging.Formatter('%(asctime)s %(message)s'))

    def emit(self, record):
        room = record.name
        status = getattr(record, 'status', {})
        try:
            send(room, record.getMessage(), log_type='log_message',
                 level=record.levelname, status=status)
        except (RedisError, RedisConnectionError, OSError, RuntimeError) as e:
            logger.debug(e)


class LogConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        '''join room'''
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        try:
            await self.channel_layer.group_add(
                    self.room_name,
                    self.channel_name
                )

            await self.accept()
        # redis is not up, what to do?
        except (RedisError, RedisConnectionError, OSError) as e:
            logger.debug(e)

    async def disconnect(self, close_code):
        '''leave room'''
        await self.channel_layer.group_discard(
            self.room_name,
            self.channel_name
        )

    async def log_message(self, event):
        '''send "log_message"'''
        try:
            await self.send(text_data=json.dumps({
                'message': event['message'],
                'level': event.get('level'),
                'timestamp': event.get('timestamp'),
                'status': event.get('status')
            }))
        except (RedisError, OSError, RedisConnectionError) as e:
            logger.debug(e)
