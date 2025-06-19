class BaseFixture(object):
    def __init__(self, data):
        self.data = data


class JSONFixture(BaseFixture):
    def keys(self):
        return self.data.keys()

    def length(self):
        return len(self.data)
