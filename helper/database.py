import importlib
import inspect
import pkgutil


def init_db():
    """
    Initialize the database.
    """
    from repository.base_repository import BaseRepository
    from service.database_manager import DatabaseManager

    base_package = "repository"
    package = importlib.import_module(base_package)

    discovered_repositories = {}
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{base_package}.{module_name}")

        discovered_repositories |= {
            name: obj_type
            for name, obj_type in inspect.getmembers(module)
            if inspect.isclass(obj_type)
               and issubclass(obj_type, BaseRepository)
               and not inspect.isabstract(obj_type)
        }

    database_manager = DatabaseManager()

    # create tables
    for repository_type in discovered_repositories.values():
        repository = repository_type()
        table = repository.table_name
        database_manager.create_table(table, repository.model_fields_definition)

    # create relations
    for repository_type in discovered_repositories.values():
        repository = repository_type()
        table = repository.table_name

        for relation in repository.model_relations_definition:
            database_manager.create_relation(table, relation)
