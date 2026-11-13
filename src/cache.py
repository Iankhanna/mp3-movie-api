import json
import logging

import fakeredis

logger = logging.getLogger(__name__)

class MovieCache:
    def __init__(self):
        self.client = fakeredis.FakeRedis(decode_responses=True)

    def make_key(self, limit):
        return f"movies:limit:{limit}"

    def get(self, limit):
        key = self.make_key(limit)
        cached = self.client.get(key)

        if cached is None:
            logger.debug("Cache MISS: %s", key)
            return None

        logger.debug("Cache HIT: %s", key)
        return json.loads(cached)

    def set(self, limit, response):
        key = self.make_key(limit)
        self.client.set(key, json.dumps(response), ex=90)

    def invalidate(self):
        self.client.flushdb()
        logger.debug("Invalidated movie cache")