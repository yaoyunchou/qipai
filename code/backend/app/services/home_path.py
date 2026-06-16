from app.models.user import UserRole

ROLE_HOME: dict[UserRole, str] = {
    UserRole.CASHIER: "/floor",
    UserRole.MANAGER: "/admin",
    UserRole.SHAREHOLDER: "/reports",
    UserRole.ADMIN: "/admin",
}


def home_path_for(role: UserRole) -> str:
    return ROLE_HOME[role]
