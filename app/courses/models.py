from sqlalchemy import Boolean, CheckConstraint, Column, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, func, select
from sqlalchemy.orm import column_property, relationship
from sqlalchemy.sql.expression import text
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    published = Column(Boolean, server_default="FALSE", nullable=False)
    rating = Column(Numeric(3, 1), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()"))

    __table_args__ = (
        CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="ck_courses_rating_range"),
        Index(
            "ix_courses_published_created_at_id",
            "created_at",
            "id",
            postgresql_where=text("published = true"),
            postgresql_ops={"created_at": "DESC", "id": "DESC"},
        ),
    )

    instructors = relationship(
        "CourseInstructor",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    ratings = relationship(
        "CourseRating",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    enrollments = relationship(
        "CourseEnrollment",
        back_populates="course",
        cascade="all, delete-orphan",
    )


class CourseInstructor(Base):
    __tablename__ = "course_instructors"

    id = Column(Integer, primary_key=True, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    is_primary = Column(Boolean, server_default="FALSE", nullable=False)
    added_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (UniqueConstraint("course_id", "user_id", name="uq_course_instructor"),)

    course = relationship("Course", back_populates="instructors")
    user = relationship("User", back_populates="instructed_courses")


class CourseRating(Base):
    __tablename__ = "course_ratings"

    id = Column(Integer, primary_key=True, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Numeric(3, 1), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_course_rating"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_course_rating_range"),
    )

    course = relationship("Course", back_populates="ratings")
    user = relationship("User", back_populates="course_ratings")


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"

    id = Column(Integer, primary_key=True, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    enrolled_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (UniqueConstraint("course_id", "user_id", name="uq_course_enrollment"),)

    course = relationship("Course", back_populates="enrollments")
    user = relationship("User", back_populates="course_enrollments")


# Add enrolled_count as computed column (avoids loading all enrollments)
Course.enrolled_count = column_property(
    select(func.count(CourseEnrollment.id))
    .where(CourseEnrollment.course_id == Course.id)
    .correlate(Course)
    .scalar_subquery()
)
