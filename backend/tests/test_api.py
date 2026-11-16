import asyncio

from app import controller


def _complete_full_session(db, template, course_units):
    """Build a completed session straight through the controller, bypassing
    HTTP (and its rate limiter) so analytics tests can seed real data fast."""
    session = controller.create_session(db, template, course_units, is_demo=False)
    db.flush()
    criteria = controller.ordered_criteria(db, template.id)
    for _ in range(500):
        if session.status == "completed":
            return session
        course_unit_id = controller.current_course_unit_id(session)
        if controller._missing_criterion(session, course_unit_id, criteria) is None:
            missing_rating = controller._missing_required_rating(
                session, course_unit_id, criteria
            )
            if missing_rating is not None:
                controller.submit_rating(db, session, missing_rating.key, 4, False)
            else:
                controller.submit_evaluation(db, session)
            db.flush()
            continue
        asyncio.run(
            controller.process_message(
                db, session, "Clear and well organised, good practical examples.", "text"
            )
        )
        db.flush()
    raise AssertionError("Session did not complete in time")


def _login(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "reviewer@qaai.local", "password": "qaai-demo-2026"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _run_full_evaluation(client, content="The sessions were clear and helpful, with good practical examples."):
    """Start a session and answer through every course until it's ready to submit."""
    response = client.post("/api/evaluations", json={"template_key": "umu-year3-review"})
    assert response.status_code == 201, response.text
    view = response.json()
    session_id = view["session_id"]
    assert view["expecting"] == "message"
    assert view["messages"][0]["role"] == "assistant"

    for _ in range(300):
        if view["expecting"] == "review":
            break
        if view["expecting"] == "rating":
            response = client.post(
                f"/api/evaluations/{session_id}/rating",
                json={"criterion_key": view["rating_criterion"], "rating": 4},
            )
        else:
            response = client.post(
                f"/api/evaluations/{session_id}/messages",
                json={"content": content, "source": "text"},
            )
        assert response.status_code == 200, response.text
        view = response.json()
    else:
        raise AssertionError("Evaluation did not reach review in time")

    return session_id, view


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "ok"
    assert body["ai_engine"] == "disabled"


def test_full_student_flow(client, db, seeded):
    session_id, view = _run_full_evaluation(client)
    assert view["expecting"] == "review"
    assert len(view["course_units"]) == 6
    assert all(course["status"] == "done" for course in view["course_units"][:-1])

    response = client.get(f"/api/evaluations/{session_id}/review")
    assert response.status_code == 200
    review = response.json()
    assert review["responses"]
    assert set(review["course_units"]) == {c["course_unit"] for c in view["course_units"]}
    assert review["ready_to_submit"] is True

    response = client.post(f"/api/evaluations/{session_id}/submit")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"

    # Duplicate submission is idempotent, and the conversation is closed.
    response = client.post(f"/api/evaluations/{session_id}/submit")
    assert response.status_code == 200
    response = client.post(
        f"/api/evaluations/{session_id}/messages",
        json={"content": "One more thought.", "source": "text"},
    )
    assert response.status_code == 400


def test_cannot_submit_incomplete_evaluation(client, seeded):
    response = client.post("/api/evaluations", json={"template_key": "umu-year3-review"})
    session_id = response.json()["session_id"]
    response = client.post(f"/api/evaluations/{session_id}/submit")
    assert response.status_code == 400


def test_analytics_requires_authentication(client):
    assert client.get("/api/analytics/overview").status_code == 401
    assert client.get("/api/analytics/records").status_code == 401


def test_invalid_login(client, reviewer):
    response = client.post(
        "/api/auth/login",
        json={"email": "reviewer@qaai.local", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_dashboard_analytics_is_database_backed(client, db, seeded, reviewer):
    institution, faculty, department, course, course_units, template = seeded
    for _ in range(2):
        _complete_full_session(db, template, course_units)
    db.commit()

    headers = _login(client)

    response = client.get("/api/analytics/overview", headers=headers)
    assert response.status_code == 200, response.text
    overview = response.json()
    assert overview["total_evaluations"] >= 2
    assert overview["completed_evaluations"] >= 2
    assert overview["total_responses"] >= 2 * 6 * 8
    assert overview["average_rating"] is not None

    response = client.get("/api/analytics/criteria", headers=headers)
    assert response.status_code == 200
    criteria = response.json()
    assert len(criteria) == 8
    assert all(item["response_count"] >= 2 * 6 for item in criteria)

    response = client.get("/api/analytics/themes", headers=headers)
    assert response.status_code == 200
    assert response.json()

    response = client.get("/api/analytics/records?page=1&page_size=10", headers=headers)
    assert response.status_code == 200
    page = response.json()
    assert page["total"] >= 2 * 6 * 8
    assert len(page["items"]) == 10
    first = page["items"][0]
    assert first["evaluation_id"].startswith("EV-")
    assert "student" not in {key.lower() for key in first.keys()}

    response = client.get("/api/analytics/comments", headers=headers)
    assert response.status_code == 200
    assert response.json()

    response = client.get("/api/analytics/overview?mode=live", headers=headers)
    assert response.status_code == 200
    assert response.json()["live_evaluations"] >= 2
