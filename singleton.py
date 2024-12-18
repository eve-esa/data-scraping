class singleton:
    instances = {}

    def __new__(cls, class_):
        def getinstance(*args, **kwargs):
            if class_ not in cls.instances:
                cls.instances[class_] = class_(*args, **kwargs)
            return cls.instances[class_]

        return getinstance
