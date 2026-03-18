from enum import Enum


class ProjectStatus(str, Enum):
    ACTIVE = "activo"
    PAUSED = "pausado"
    COMPLETED = "completado"


class TaskStatus(str, Enum):
    PENDING = "pendiente"
    IN_PROGRESS = "en_progreso"
    BLOCKED = "bloqueada"
    DONE = "hecha"


class TaskPriority(str, Enum):
    LOW = "baja"
    MEDIUM = "media"
    HIGH = "alta"