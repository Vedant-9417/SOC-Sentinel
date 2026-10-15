from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from .models import User
from .auth import hash_password


def init_database():
    # Create all database tables
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    try:
        # Check whether the admin user already exists
        existing_user = (
            db.query(User)
            .filter(User.username == "admin")
            .first()
        )

        if existing_user:
            print("Admin user already exists.")
            return

        # Create default administrator
        admin = User(
            username="admin",
            password_hash=hash_password("ChangeMe123!"),
            role="admin",
        )

        db.add(admin)
        db.commit()

        print("Database initialized successfully.")
        print("Default login:")
        print("  Username: admin")
        print("  Password: ChangeMe123!")

    finally:
        db.close()


if __name__ == "__main__":
    init_database()