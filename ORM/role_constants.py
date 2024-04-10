from enum import Enum as PyEnum

class Roles(PyEnum):
    STUDENT = "Student"
    ADMIN = "Admin"

permission_names = {
    Roles.ADMIN.value: ["create_qp", "update_qp"]
}