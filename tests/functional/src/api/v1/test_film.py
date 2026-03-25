from http import HTTPStatus

import pytest

# В es_data_movies 60 фильмов со случайными uuid + 1 хардкодный
TOTAL_MOVIES_IN_FIXTURE = 61


@pytest.mark.parametrize(
    "input_data, expected_answer",
    [
        (
            {"film_id": "608c4567-0b8a-49a0-88fb-82770c5b2f61"},
            {"status": HTTPStatus.OK, "title": "The movie"},
        ),
        (
            {"film_id": "00000000-0000-0000-0000-000000000000"},
            {"status": HTTPStatus.NOT_FOUND, "detail": "film not found"},
        ),
        (
            {"film_id": "00000000-0000-0000-0000-0000000000000"},
            {
                "status": HTTPStatus.BAD_REQUEST,
                "detail": "Invalid film ID format. Must be a valid UUID v4.",
            },
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_film_details(
    es_write_data,
    es_data_movies,
    make_get_request,
    input_data: dict,
    expected_answer: dict,
):
    """Тест получения информации о фильме"""
    await es_write_data(es_data_movies, "movies")
    film_id = input_data["film_id"]

    response = await make_get_request("/films", f"/{film_id}")

    assert response["status"] == expected_answer["status"]
    if response["status"] == HTTPStatus.OK:
        assert response["body"]["uuid"] == film_id
        assert response["body"]["title"] == expected_answer["title"]
    else:
        assert response["body"]["detail"] == expected_answer["detail"]


@pytest.mark.parametrize(
    "query_data, expected_answer",
    [
        (
            {},
            {
                "status": HTTPStatus.OK,
                "items_len": 50,
                "total": TOTAL_MOVIES_IN_FIXTURE,
            },
        ),
        (
            {"genre": "2fec4f4f-7f84-475c-ad28-791ce135bd2e"},
            {"status": HTTPStatus.OK, "items_len": 1, "total": 1},
        ),
        (
            {"genre": "00000000-0000-0000-0000-000000000000"},
            {"status": HTTPStatus.OK, "items_len": 0, "total": 0},
        ),
        (
            {
                "genre":
                # wrong uuid format
                "00000000-0000-0000-0000-0000000000000"
            },
            {"status": HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error": True},
        ),
        (
            {"page": 0},
            {"status": HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error": True},
        ),
        (
            {"page": 10000},
            {
                "status": HTTPStatus.OK,
                "items_len": 0,
                "total": TOTAL_MOVIES_IN_FIXTURE,
            },
        ),
        (
            {"size": 0},
            {"status": HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error": True},
        ),
        (
            {"size": 2},
            {"status": HTTPStatus.OK, "items_len": 2, "total": TOTAL_MOVIES_IN_FIXTURE},
        ),
        (
            {"size": 101},
            {"status": HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error": True},
        ),
        (
            {"sort": "random"},
            {"status": HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error": True},
        ),
    ],
)
@pytest.mark.asyncio
async def test_list_films(
    es_write_data,
    es_data_movies,
    make_get_request,
    query_data: dict,
    expected_answer: dict,
):
    """Тест получения списка фильмов: тело ответа { items, total }."""
    await es_write_data(es_data_movies, "movies")

    response = await make_get_request("/films", "", query_data)

    assert response["status"] == expected_answer["status"]
    body = response["body"]

    if response["status"] == HTTPStatus.OK:
        assert "items" in body
        assert "total" in body
        assert len(body["items"]) == expected_answer["items_len"]
        assert body["total"] == expected_answer["total"]
    elif expected_answer.get("validation_error"):
        assert "detail" in body
