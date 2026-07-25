class NotionIntegrationError(RuntimeError):
    """Erro base da integração com o Notion."""


class NotionConfigurationError(NotionIntegrationError):
    """Configuração ou variável de ambiente ausente."""


class NotionUnitNotFoundError(NotionIntegrationError):
    """Knowledge Unit não encontrada no Notion."""


class DuplicateNotionUnitError(NotionIntegrationError):
    """Mais de uma página possui o mesmo KIR ID."""


class NotionSyncConflictError(NotionIntegrationError):
    """O estado do Notion divergiu do estado esperado pela KIR."""