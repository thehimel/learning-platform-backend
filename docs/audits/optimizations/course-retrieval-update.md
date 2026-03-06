# Course Retrieval & Update — Optimization Recommendations

Optimization suggestions for the features implemented in commit `fa25c42` (course retrieval and update endpoints), aligned with industry standards.

---

## Summary

| # | Area | Priority | Effort | Impact | Status |
|---|------|----------|--------|--------|--------|
| 1 | Auth check optimization | High | Low | Fewer queries, less data loaded | ✅ Done |
| 2 | Centralized exception handling | Medium | Medium | Maintainability | ✅ Done |
| 3 | Path param `id` convention | Low | — | Consistency | ✅ Done |
| 4 | Pagination for `get_courses` | High | Medium | Scalability | ✅ Done |
| 5 | `update_course` bulk insert + return from update logic | Medium | Low | Fewer round-trips | ✅ Done |
| 6 | `enrolled_count` via SQL | Medium | Low | Performance | ✅ Done |
| 7 | `rate_course` background task | Medium | Low | Faster response | ✅ Done |
| 8 | IDOR: unpublished course visibility | Medium | Medium | Security | ✅ Done |
| 9 | Input validation (description max_length, XSS escape) | Medium | Low | Security | ✅ Done |
| 10 | Mass assignment (no sensitive fields in schema) | Low | Low | Security | ✅ Done |
| 11 | Audit logging for course updates | Medium | Medium | Security/compliance | Pending |
| 12 | Per-route rate limits | Low | Low | Abuse prevention | Pending |
| 13 | Indexes (verify common access patterns) | Medium | Low | Performance | ✅ Done |

---

## Code Quality

### 1. Authorization Check Optimization in `update_course` ✅ Implemented

**Previous:** Loaded full course with instructors to check membership.

```python
course = await get_course(id, session)
is_instructor_of_course = any(ci.user_id == current_user.id for ci in course.instructors)
if not is_admin and not is_instructor_of_course:
    raise NotInstructorOfCourseError()
```

**Implemented:** Use an existence check instead of loading the full course when only checking permission:

```python
if not await _course_exists(session, id):
    raise CourseNotFoundError()

is_admin = current_user.role == UserRole.admin
if not is_admin:
    stmt = select(
        exists().where(
            CourseInstructor.course_id == id,
            CourseInstructor.user_id == current_user.id,
        )
    )
    result = await session.execute(stmt)
    is_instructor_of_course = result.scalar_one()
    if not is_instructor_of_course:
        raise NotInstructorOfCourseError()
```

The full course is only fetched at the end for the response.

---

### 2. Centralized Exception Handling in Router ✅ Implemented

**Previous:** Each route handler had repetitive `try/except` blocks mapping domain exceptions to HTTP responses.

```python
@router.get("/{id}")
async def get_course(id: int, session: AsyncSession = Depends(get_db)):
    try:
        return await get_course_service(id, session)
    except CourseNotFoundError:
        raise HTTPException(status_code=404, detail=error_detail(CourseErrorCode.course_not_found, "Course not found."))
```

**Implemented:** Route handlers delegate to the service; exceptions bubble up to app-registered handlers.

```python
@router.get("/{id}")
async def get_course(id: int, session: AsyncSession = Depends(get_db)):
    return await get_course_service(id, session)
```

---

### 3. Path Parameter Naming ✅ Use `id`

**Convention:** Use `id` in route handlers and service layer for path parameters (e.g. `/{id}`). Keeps code concise and consistent across router and service.

**Current (implemented):**

```python
@router.get("/{id}", response_model=CourseRead)
async def get_course(id: int, session: AsyncSession = Depends(get_db)) -> Course:
    return await get_course_service(id, session)

async def get_course(id: int, session: AsyncSession) -> Course:
    stmt = select(Course).where(Course.id == id).options(*_COURSE_LOAD_OPTIONS)
    ...
```

---

## Performance

### 4. `get_courses` — Pagination ✅ Implemented

**Previous:** Loads all courses into memory. Will not scale with large datasets.

```python
async def get_courses(session: AsyncSession) -> list[Course]:
    stmt = (
        select(Course)
        .options(*_COURSE_LOAD_OPTIONS)
        .order_by(Course.created_at.desc(), Course.id.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())
```

**Implemented:** Limit/offset pagination with `CourseListResponse` (`items`, `total`, `limit`, `offset`). API accepts `limit` (default 20, max 100) and `offset` query params.

```python
async def get_courses(
    session: AsyncSession,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Course], int]:
    base_stmt = (
        select(Course)
        .options(*_COURSE_LOAD_OPTIONS)
        .order_by(Course.created_at.desc(), Course.id.desc())
    )
    count_stmt = select(func.count()).select_from(Course)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()
    stmt = base_stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    courses = list(result.scalars().unique().all())
    return courses, total
```

---

### 5. `update_course` — Multiple Round-Trips ✅ Implemented

**Current flow:**

```
1. get_course (SELECT with eager loads)
2. Optional update(Course)
3. Optional delete(CourseInstructor) + add_all
4. commit
5. Re-fetch course for response
```

**Previous (instructor update):**

```python
await session.execute(delete(CourseInstructor).where(CourseInstructor.course_id == id))
course_instructors = [
    CourseInstructor(course_id=id, user_id=instructor.id, is_primary=(index == 0))
    for index, instructor in enumerate(instructors)
]
session.add_all(course_instructors)
await session.commit()
stmt = select(Course).where(Course.id == id).options(*_COURSE_LOAD_OPTIONS)
return (await session.execute(stmt)).scalars().unique().one()  # Re-fetch
```

**Implemented (instructor update + return from update logic):**

```python
await session.execute(delete(CourseInstructor).where(CourseInstructor.course_id == id))
if instructors:
    await session.execute(
        insert(CourseInstructor).values([
            {"course_id": id, "user_id": instructor.id, "is_primary": index == 0}
            for index, instructor in enumerate(instructors)
        ])
    )

# Fetch in same transaction (sees uncommitted changes); return without re-fetch after commit.
stmt = select(Course).where(Course.id == id).options(*_COURSE_LOAD_OPTIONS)
result = await session.execute(stmt)
course = result.scalars().unique().one()
await session.commit()
return course
```

Uses in-memory merge: SELECT before commit so the course reflects all changes; with `expire_on_commit=False`, the returned object stays loaded—no separate re-fetch after commit.

---

### 6. `enrolled_count` — Loads All Enrollments ✅ Implemented

**Previous:** `enrolled_count` was computed as `len(data.enrollments)` after loading all enrollment rows.

**Previous:**

```python
# _COURSE_LOAD_OPTIONS loaded all enrollments
selectinload(Course.enrollments),

# CourseRead model_validator
"enrolled_count": len(data.enrollments),
```

**Implemented:**

```python
# Course model — column_property with correlated subquery
Course.enrolled_count = column_property(
    select(func.count(CourseEnrollment.id))
    .where(CourseEnrollment.course_id == Course.id)
    .correlate(Course)
    .scalar_subquery()
)

# _COURSE_LOAD_OPTIONS — no enrollments load
_COURSE_LOAD_OPTIONS = (
    selectinload(Course.instructors).selectinload(CourseInstructor.user),
)

# CourseRead model_validator — uses data.enrolled_count from DB
"enrolled_count": data.enrolled_count if hasattr(data, "enrolled_count") else ...,
```

The DB computes the count via a subquery; enrollment rows are no longer loaded.

---

### 7. `rate_course` — Rating Recompute on Every Request ✅ Implemented (background task)

**Previous:** Recomputed `AVG(rating)` synchronously on every rate/update.

**Implemented:** Rating recompute runs as a FastAPI `BackgroundTasks` after the response is sent. In tests (`RATING_RECOMPUTE_ASYNC=false`), recompute runs inline using the request session to avoid event-loop issues.

**Previous:**

```python
# Recompute course aggregate rating (blocking)
avg_stmt = select(func.avg(CourseRating.rating)).where(CourseRating.course_id == id)
avg_result = await session.execute(avg_stmt)
avg_rating = avg_result.scalar_one_or_none()
await session.execute(
    update(Course).where(Course.id == id).values(rating=avg_rating)
)
```

**Implemented:**

```python
# Router: schedule recompute after response
rating = await rate_course_service(id, payload, current_user, session)
if settings.rating_recompute_async:
    background_tasks.add_task(recompute_course_rating, id)
else:
    await recompute_course_rating(id, session)  # Inline for tests
return rating
```

Faster response; aggregate updates shortly after.

---

## Security

### 8. IDOR on GET /courses/{id} ✅ Implemented

**IDOR (Insecure Direct Object Reference):** A vulnerability where an API exposes internal object IDs (e.g. course IDs) and allows users to access resources they should not by guessing or iterating over IDs. An attacker can probe `/courses/1`, `/courses/2`, etc. to discover or access non-public content.

**Previous:** GET was public for all courses; unpublished courses were visible to anyone.

**Implemented:**

- Unpublished courses return 404 for unauthenticated requests and for authenticated non-instructors/non-admins.
- Instructors of the course and admins can access unpublished courses.
- `get_courses` list returns only published courses (avoids leaking unpublished IDs).
- Optional auth via `current_user_optional`; visibility checked in service.

```python
# Service: if unpublished, require instructor or admin
if not course.published:
    if current_user is None:
        raise CourseNotFoundError()
    is_admin = current_user.role == UserRole.admin
    is_instructor = any(ci.user_id == current_user.id for ci in course.instructors)
    if not is_admin and not is_instructor:
        raise CourseNotFoundError()
```

---

### 9. Input Validation ✅ Implemented

**Previous:** `title` had `max_length=500`; `description` had no length limit; no XSS sanitization.

**Implemented:**

```python
MAX_DESCRIPTION_LENGTH = 5000

class CourseUpdate(BaseModel):
    title: Annotated[str | None, Field(default=None, min_length=1, max_length=500)] = None
    description: Annotated[str | None, Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)] = None
    ...

    @model_validator(mode="after")
    def escape_html_fields(self) -> "CourseUpdate":
        """Escape title and description for safe HTML rendering."""
        if self.title is not None:
            object.__setattr__(self, "title", _escape_html(self.title))
        if self.description is not None:
            object.__setattr__(self, "description", _escape_html(self.description))
        return self
```

- `description` has `max_length=5000` in `CourseCreate` and `CourseUpdate`.
- `instructor_ids` UUIDs validated by Pydantic.
- `html.escape()` (via `_escape_html`) applied to `title` and `description` before storage to mitigate XSS.

---

### 10. Mass Assignment ✅ Implemented

**Previous:** `CourseUpdate` used optional fields with no protection against extra fields. Clients could send unknown fields (e.g. `rating`, `created_at`) which were silently ignored; a future schema change could accidentally expose sensitive fields.

```python
class CourseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    published: bool | None = None
    instructor_ids: list[uuid.UUID] | None = None
```

**Implemented:** Schema forbids extra fields and documents the intentional limitation. Unknown fields cause a 422 validation error.

```python
class CourseUpdate(BaseModel):
    """
    Intentionally limited to title, description, published, instructor_ids.
    Sensitive fields (e.g. rating, created_at) omitted to prevent mass assignment.
    Clients sending extra fields receive a validation error.
    """

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    published: bool | None = None
    instructor_ids: list[uuid.UUID] | None = None
```

---

### 11. Audit Logging for Course Updates

**Current:** No audit trail for who changed what and when.

**Current:**

```python
# update_course performs updates with no logging
await session.execute(update(Course).where(Course.id == id).values(**update_data))
# ... instructor updates ...
await session.commit()
# No record of actor, action, or before/after state
```

**Recommendation:** Add audit logging for course updates (actor, action, timestamp, before/after) for compliance and forensics.

---

### 12. Rate Limiting

**Current:** Global rate limiting exists.

**Current:**

```python
# app/limiter.py — applies to all routes
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
)
```

**Recommendation:** Consider stricter per-route limits for course creation, updates, and enroll/unenroll to mitigate abuse and scraping.
---

## Database

### 13. Indexes ✅ Implemented

**Implemented:** Partial index on `courses` for `get_courses` ordering when filtering published only (common case for unauthenticated and many authenticated requests):

```python
# app/courses/models.py
Index(
    "ix_courses_published_created_at_id",
    "created_at",
    "id",
    postgresql_where=text("published = true"),
    postgresql_ops={"created_at": "DESC", "id": "DESC"},
),
```

**Existing indexes (from initial migration):**

- `course_instructors`: `ix_course_instructors_course_id`, `ix_course_instructors_user_id`, `uq_course_instructor`
- `course_enrollments`: `ix_course_enrollments_course_id`, `ix_course_enrollments_user_id`, `uq_course_enrollment`
- `course_ratings`: indexes on `course_id`, `user_id`; `uq_course_rating` for upsert
