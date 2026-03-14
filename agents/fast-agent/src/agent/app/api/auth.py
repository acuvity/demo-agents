"""Authentication module using Descope for session validation."""
import sys
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from descope import AuthException, DescopeClient  # type: ignore[attr-defined]

from app.db.database import get_db
from app.models.chat import User
from app.core.config import settings
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)

# Initialize the security scheme
security = HTTPBearer()


class Auth:
    """Handles Descope-based authentication and user session validation."""

    def __init__(self):
        try:
            if settings.DESCOPE_PROJECT_ID:
                self.descope_client = DescopeClient(
                    project_id=settings.DESCOPE_PROJECT_ID
                )
            else:
                self.descope_client = None
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Failed to create DescopeClient: %s", e)
            sys.exit(1)

    def validate_session(self, db: Session, session_token: str):
        """Validate a Descope session token and return the user id."""
        if not self.descope_client:
            logger.warning("No authorization active.")
            return 1

        # Authorize with Descope
        try:
            jwt_response = self.descope_client.validate_session(
                session_token=session_token
            )
            user_id = jwt_response["userId"]
            logger.info(
                "Successfully validated user session: %s for user: %s",
                jwt_response,
                user_id,
            )
            user = db.query(User).filter(User.username == user_id).first()
            if user:
                logger.debug("User found in database: %s", user)
                return user.id
            logger.info("User not found in database, creating new user: %s", user_id)
            user = User(
                username=user_id,
                email=f"{user_id}@email.com",  # Replace with actual email from JWT
                hashed_password=get_password_hash(
                    "dummy_password"
                ),  # Replace with actual password hashing
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user.id
        except AuthException as error:
            logger.error("Could not validate user session. Error: %s", error)
            return 0

    def get_verified_user_id(
        self,
        db: Session = Depends(get_db),
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ):
        """Extract and verify the user id from the bearer token."""
        token = credentials.credentials
        user_id = self.validate_session(db, token)
        if not user_id:  # type: ignore[truthy-function]
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return user_id


auth = Auth()
