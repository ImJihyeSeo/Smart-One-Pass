# session_manager.py
class UserSession:
    _instance = None
    user_id = None
    name = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def login(self, user_id, name=None):
        self.user_id = user_id
        self.name = name

    def logout(self):
        self.user_id = None
        self.name = None
        
    def get_user_id(self):
        return self.user_id