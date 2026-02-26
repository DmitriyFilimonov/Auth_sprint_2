from http import HTTPStatus


import pytest

from tests.functional.models.user import UserCreate


@pytest.mark.parametrize(
    "input_data, expected_answer",
    [
        (
            UserCreate(
                login="admin",
                email="admin@admin.domain",
                first_name="Firstname",
                last_name="Lastname",
                password="passW0RD_LongerThan10",
            ).dict(),
            {
                "status": HTTPStatus.CREATED,
            },
        ),
    ],
)
@pytest.mark.asyncio
async def test_signup(
    make_auth_request, input_data: dict, expected_answer: dict, clear_auth_db_tables
):
    await clear_auth_db_tables()

    response = await make_auth_request("post", "/signup", input_data)

    assert response["status"] == expected_answer["status"]
