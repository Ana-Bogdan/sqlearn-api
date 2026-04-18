class SandboxDatabaseRouter:
    """Keep the ``sandbox`` DB alias out of Django's ORM and migration flow.

    The alias is reserved for raw SQL executed against per-user schemas, and
    should never carry app models or receive migrations.
    """

    SANDBOX = "sandbox"

    def db_for_read(self, model, **hints):
        return None

    def db_for_write(self, model, **hints):
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == self.SANDBOX:
            return False
        return None
