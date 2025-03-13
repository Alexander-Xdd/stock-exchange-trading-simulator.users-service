from pg_adapter import PostgresAdapter


class UsersManager:
    def __init__(self, limit, page, sort_type):
        self._psql = PostgresAdapter()


    def get(self):
        pass
