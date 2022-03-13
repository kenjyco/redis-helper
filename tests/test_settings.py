import redis_helper as rh
import settings_helper as sh


class TestEnv:
    def test_app_env_is_test(self):
        assert sh.APP_ENV == 'test'

    def test_redis_url_ends_with_9(self):
        redis_url = rh.SETTINGS.get('redis_url', '')
        assert redis_url != '' and redis_url.endswith('9')
